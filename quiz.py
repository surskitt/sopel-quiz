#! /usr/bin/env python

import requests
from sopel.module import commands
import re


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
        answer = re.sub(r'^(the|a|an) |\<.*?\>', '', answer)
        return answer.lower()

    def attempt(self, attempt):
        return (attempt is not None and self.checked_answer in attempt.lower())


class Quiz():
    def __init__(self):
        self.scores = {}
        self.qno = 0
        self.question = None

    def start(self):
        pass

    def stop(self):
        pass

    def next_question(self):
        pass

    def get_scores(self):
        pass

    pass


def setup(bot):
    bot.memory['quiz'] = None


@commands('quiz')
def quiz(bot, trigger):
    bot.memory['quiz'] = Quiz()


@commands('qstop')
def qstop(bot, trigger):
    pass


@commands('qscores')
def qscores(bot, trigger):
    pass


@commands('qskip')
def qskip(bot, trigger):
    pass


if __name__ == "__main__":
    q = Question()
    print(q.get_question())
    attempt = input('Answer: ')
    # if attempt.lower() in q.checked_answer.lower():
    if q.attempt(attempt):
        print('Correct! The answer was {}'.format(q.answer))
    else:
        print('Nope! The answer was {}'.format(q.answer))
