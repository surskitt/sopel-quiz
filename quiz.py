#! /usr/bin/env python

import requests
from sopel.module import commands, rule
import re
from threading import Timer
from time import sleep


def setup(bot):
    bot.memory['quiz'] = None


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
        self.value = q_json['value']

    def get_question(self):
        q, c, v = self.question, self.category, self.value
        return '{} ({}) [{}]'.format(q, c, v)

    def strip_answer(self, answer):
        # strip any crap that should never be printed
        # - html tags
        answer = re.sub(r'\<.*?\>', '', answer)
        return answer

    def parse_answer(self, answer):
        # strip extraneous characters, making the question easier to answer
        # - a, an and the from the beginning
        answer = re.sub(r'^(the|a|an) |"| ?\(.*\) ?', '', answer)
        return answer.lower()

    def attempt(self, attempt):
        return (attempt is not None and self.checked_answer in attempt.lower())


class Quiz():
    def __init__(self):
        self.scores = {}
        self.qno = 0
        self.next_question()

    def get_question(self):
        return 'Question {}: {}'.format(self.qno, self.question.get_question())

    def award_user(self, user):
        if user not in self.scores:
            self.scores[user] = 1
        else:
            self.scores[user] += 1

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

    bot.memory['quiz'] = Quiz()
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
    if quiz.question.attempt(trigger.args[1]):
        bot.say('Correct! The answer was {}'.format(quiz.question.answer))
        quiz.award_user(trigger.nick)
        score = bot.memory['quiz'].get_scores()[trigger.nick]
        bot.say('{} has {} point{}!'.format(trigger.nick, score,
                                            's' * (score > 1)))

        if score == 10:
            bot.say('{} is the winner!'.format(trigger.nick))
            qscores(bot)
            bot.memory['quiz'] = None
            return

        next_q(bot)


if __name__ == "__main__":
    q = Question()
    print(q.get_question())
    attempt = input('Answer: ')
    if q.attempt(attempt):
        print('Correct! The answer was {}'.format(q.answer))
    else:
        print('Nope! The answer was {}'.format(q.answer))
