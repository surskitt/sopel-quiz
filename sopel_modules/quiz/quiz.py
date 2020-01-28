#! /usr/bin/env python

import requests
from sopel.module import commands, rule
from sopel.config.types import (StaticSection, ValidatedAttribute,
                                ChoiceAttribute, ListAttribute)
from sopel.db import SopelDB
from sopel.formatting import colors, color
import re
from threading import Timer
from time import sleep


class QuizSection(StaticSection):
    win_method = ChoiceAttribute('win_method', ['points', 'score'],
                                 default='points')
    points_to_win = ValidatedAttribute('points_to_win', int, default=10)
    score_to_win = ValidatedAttribute('score_to_win', int, default=7000)
    db_users = ListAttribute('db_users')


def setup(bot):
    bot.config.define_section('quiz', QuizSection)
    bot.memory['quiz'] = None


def configure(config):
    config.define_section('quiz', QuizSection, validate=False)
    config.quiz.configure_setting('win_method', 'Win by points or score?')
    if config.quiz.win_method == 'points':
        config.quiz.configure_setting('points_to_win',
                                      'How many points are needed to win?')
    else:
        config.quiz.configure_setting('score_to_win',
                                      'What score is needed to win?')
    config.quiz.configure_setting('db_users',
                                  'Which users can start tracked quizzes?')


def shutdown(bot):
    if bot.memory.contains('qtimer'):
        bot.memory['qtimer'].cancel()


class Question():
    def __init__(self):
        r = requests.get('http://jservice.io/api/random')
        q_json = r.json()[0]
        self.question = q_json['question'].strip()
        self.answer = self.strip_answer(q_json['answer'])
        self.checked_answer = self.parse_answer(self.answer)
        self.category = q_json['category']['title']
        self.value = q_json['value'] or 100
        self.answered = False
        r.close()

    def get_question(self):
        q, c, v = self.question, self.category, self.value
        return '{} ({}) [{}]'.format(q, c, v)

    def strip_answer(self, answer):
        # strip any crap that should never be printed
        # - html tags
        # - \'
        answer = re.sub(r'\<.*?\>|\\(?=\')', '', answer)
        return answer

    def parse_answer(self, answer):
        # strip extraneous characters, making the question easier to answer
        # - a, an and the from the beginning
        # - quotes
        # - parenthesised sections
        answer = re.sub(r'^"?(the|a|an) |"| ?\(.*\) ?|s$|', '', answer,
                        flags=re.I)
        answer = re.sub(r'&', 'and', answer)
        return answer.lower()

    def attempt(self, attempt):
        return (attempt is not None and self.checked_answer in attempt.lower())


class Quiz():
    def __init__(self, starter):
        self.scores = {}
        self.qno = 0
        self.next_question()
        self.starter = starter

    def get_question(self):
        return 'Question {}: {}'.format(self.qno, self.question.get_question())

    def award_user(self, user, count):
        if user not in self.scores:
            self.scores[user] = count
        else:
            self.scores[user] += count

    def next_question(self):
        self.qno += 1
        self.question = Question()

    def get_scores(self):
        return self.scores


@commands('quiz')
def quiz(bot, trigger):
    if bot.memory['quiz']:
        bot.say('Quiz is already running')
        return

    bot.say('Quiz started by {}'.format(trigger.nick))
    if bot.config.quiz.win_method == 'points':
        win_value = bot.config.quiz.points_to_win
        bot.say('First to answer {} questions wins!'.format(win_value))
    else:
        win_value = bot.config.quiz.score_to_win
        bot.say('First to {} points wins!'.format(win_value))

    bot.memory['quiz'] = Quiz(trigger.nick)
    bot.say(bot.memory['quiz'].get_question())
    bot.memory['qtimer'] = Timer(30, qtimeout, args=[bot])
    bot.memory['qtimer'].start()


@commands('qstop')
def qstop(bot, trigger):
    if not bot.memory['quiz']:
        bot.say('No quiz running!')
        return

    bot.say('Quiz stopped by {}'.format(trigger.nick))
    bot.memory['quiz'] = None
    bot.memory['qtimer'].cancel()


@commands('qscores')
def qscores(bot, trigger=None):
    if not bot.memory['quiz']:
        bot.say('No quiz running!')
        return

    if not bot.memory['quiz'].get_scores():
        bot.say('No one has scored any points yet!')
        return

    scores = sorted(bot.memory['quiz'].get_scores().items(),
                    key=lambda x: x[1], reverse=True)

    bot.say('Current scores:')
    for quizzer, score in scores:
        score = int(score)
        bot.say('{}: {} point{}'.format(quizzer, score, 's' * (score != 1)))


@commands('qwins')
def qwins(bot, trigger):
    db = SopelDB(bot.config)

    winners = db.execute(
        'SELECT canonical, value from nicknames JOIN nick_values '
        'ON nicknames.nick_id = nick_values.nick_id '
        'WHERE key = ?',
        ['quiz_wins']).fetchall()

    if winners:
        bot.say('Overall quiz win counts')
        for user, count in sorted(winners, key=lambda x: x[1], reverse=True):
            bot.say('{}: {}'.format(user, count))
    else:
        bot.say('No one has won yet!')


def reset_timer(bot):
    bot.memory['qtimer'].cancel()
    bot.memory['qtimer'] = Timer(30, qtimeout, args=[bot])
    bot.memory['qtimer'].start()


def next_q(bot):
    if not bot.memory['quiz'].qno % 10:
        qscores(bot)

    bot.memory['quiz'].next_question()
    sleep(5)
    bot.say(bot.memory['quiz'].get_question())
    reset_timer(bot)


@commands('qskip')
def qskip(bot, trigger):
    if not bot.memory['quiz']:
        bot.say('No quiz running!')
        return

    quiz = bot.memory['quiz']
    bot.say('Fine, the answer was {}'.format(quiz.question.answer))

    next_q(bot)


def qtimeout(bot):
    if not bot.memory['quiz']:
        return

    quiz = bot.memory['quiz']
    answer = quiz.question.answer
    bot.say('No answer within 30 seconds. The answer was {}'.format(answer))

    next_q(bot)


@rule('[^\.].*')
def handle_quiz(bot, trigger):
    if not bot.memory['quiz']:
        return

    quiz = bot.memory['quiz']
    if quiz.question.attempt(trigger.args[1]) and not quiz.question.answered:
        quiz.question.answered = True
        bot.say(color('Correct! The answer was {}'.format(quiz.question.answer),
                      colors.GREEN))
        quiz.award_user(trigger.nick, quiz.question.value
                        if bot.config.quiz.win_method == 'score' else 1)
        score = bot.memory['quiz'].get_scores()[trigger.nick]
        bot.say('{} has {} point{}!'.format(trigger.nick, score,
                                            's' * (score > 1)))

        if bot.config.quiz.win_method == 'points':
            win_value = bot.config.quiz.points_to_win
        else:
            win_value = bot.config.quiz.score_to_win
        if score >= win_value:
            bot.say('{} is the winner!'.format(trigger.nick))
            qscores(bot)

            db = SopelDB(bot.config)
            db_users = bot.config.quiz.db_users
            if not db_users or quiz.starter in db_users:
                wins = (db.get_nick_value(trigger.nick, 'quiz_wins') or 0) + 1
                db.set_nick_value(trigger.nick, 'quiz_wins', wins)
                bot.say('{} has won {} time{}'.format(trigger.nick, wins,
                                                      's' * (wins > 1)))

            bot.memory['quiz'] = None
            return

        next_q(bot)
