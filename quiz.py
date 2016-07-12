#! /usr/bin/env python

import requests
# from sopel.modules import commands


class Question():
    def __init__(self):
        r = requests.get('http://jservice.io/api/random')
        q_json = r.json()[0]
        self.question = q_json['question']
        self.answer = q_json['answer']
        self.checked_answer = self.parse_answer(self.answer)
        self.category = q_json['category']['title']
        self.value = q_json['value']

    def get_question(self):
        return '{} ({}) [{}]'.format(self.question, self.category, self.value)

    def parse_answer(self, answer):
        return answer


class Quiz():
    pass

if __name__ == "__main__":
    q = Question()
    print(q.question)
    attempt = input('Answer: ')
    if attempt.lower() in q.checked_answer.lower():
        print('Correct! The answer was {}'.format(q.answer))
    else:
        print('Nope! The answer was {}'.format(q.answer))
