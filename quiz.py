#! /usr/bin/env python

import requests
# from sopel.modules import commands


class Question():
    def __init__(self):
        r = requests.get('http://jservice.io/api/random')
        q_json = r.json()[0]
        self.question = q_json['question']
        self.answer = q_json['answer']


class Quiz():
    pass

if __name__ == "__main__":
    q = Question()
    print(q.question)
    print(q.answer)
