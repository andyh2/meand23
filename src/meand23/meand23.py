#!/usr/bin/env python3

import re
import requests
from urllib.parse import urlparse, parse_qs

LOGIN_PAGE = 'https://auth.23andme.com/login/?next=https%3A//auth.23andme.com/authorize/%3Fredirect_uri%3Dhttps%253A%252F%252Fyou.23andme.com%252Fauth_callback%252F%26response_type%3Dcode%26client_id%3Dyou%26scope%3Dopenid%2Bancestry%2Bbasic%2Bhaplogroups%2Bnames%2Bphenotypes%253Aread%253Aall%26state%3D%257B%2522origin_uri%2522%253A%2B%2522%252F%2522%257D'
AUTHORIZE_PAGE = 'https://auth.23andme.com/authorize/?redirect_uri=https%3A%2F%2Fyou.23andme.com%2Fauth_callback%2F&response_type=code&client_id=you&scope=openid+ancestry+basic+haplogroups+names+phenotypes%3Aread%3Aall&state=%7B%22origin_uri%22%3A+%22%2F%22%7D'
CHROMOSOMES = list(range(1,23)) + ['X','Y','MT']

class LoginError(Exception): pass
class MissingKitError(Exception): pass
class InvalidChromosomeError(Exception): pass

class MeAnd23:
    def __init__(self):
        self.session = None

    def login(self, email, password):
        self.session = requests.Session()
        self.session.get('https://you.23andme.com/')

        resp = self.session.get(LOGIN_PAGE)

        matches = re.search(r'csrfToken: "(.+?)"', resp.text)
        csrftoken = matches.group(1)

        resp = self.session.post(
            'https://auth.23andme.com/login/', 
            data={'username': email, 'password': password, 'next': parse_qs(urlparse(LOGIN_PAGE).query)['next']}, 
            headers={'referer': LOGIN_PAGE, 'x-csrftoken': csrftoken}
        )
        if resp.status_code != 200:
            raise LoginError(f'Bad login response: {resp.status_code}')

        headers = {
            'referer': 'https://auth.23andme.com/login/?next=https%3A//auth.23andme.com/authorize/%3Fredirect_uri%3Dhttps%253A%252F%252Fyou.23andme.com%252Fauth_callback%252F%26response_type%3Dcode%26client_id%3Dyou%26scope%3Dopenid%2Bancestry%2Bbasic%2Bhaplogroups%2Bnames%2Bphenotypes%253Aread%253Aall%26state%3D%257B%2522origin_uri%2522%253A%2B%2522%252F%2522%257D',
        }
        resp = self.session.get('https://auth.23andme.com/authorize/?redirect_uri=https%3A%2F%2Fyou.23andme.com%2Fauth_callback%2F&response_type=code&client_id=you&scope=openid+ancestry+basic+haplogroups+names+phenotypes%3Aread%3Aall&state=%7B%22origin_uri%22%3A+%22%2F%22%7D', headers=headers)  
        if resp.url != 'https://you.23andme.com/':
            raise LoginError(f'Authorization failed: did not land on you.23andme.com')
    
    def current_profile(self):
        resp = self.session.get('https://you.23andme.com/')
        matches = re.search(r'"profile_id": "(.+?)"', resp.text) 
        return matches.group(1)

    def profiles(self):
        resp = self.session.get('https://you.23andme.com/')
        matches = re.findall(r'href="/p/([a-z0-9]+?)/"', resp.text)
        return list(set(matches)) + [re.search(r'"profile_id": "(.+?)"', resp.text).group(1)]

    def use_profile(self, profile_id):
        self.session.get(f'https://you.23andme.com/p/{profile_id}/')
        assert self.current_profile() == profile_id

    def chromosome(self, cid):
        if cid not in CHROMOSOMES:
            raise InvalidChromosomeError()

        self.session.get('https://you.23andme.com/tools/data/')

        headers = {
            'authority': 'you.23andme.com',
            'pragma': 'no-cache',
            'cache-control': 'no-cache',
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'x-newrelic-id': 'UwAFVF5aGwoBU1JRBwU=',
            'x-requested-with': 'XMLHttpRequest',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36',
            'sec-gpc': '1',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
            'referer': 'https://you.23andme.com/tools/data/',
            'accept-language': 'en-US,en;q=0.9',
        }
        offset = 0
        genes = [None]
        while genes:
            params = {
                'chromosome': cid,
                'offset': offset,
            }
            resp = self.session.get('https://you.23andme.com/tools/data/', headers=headers, params=params)
            if resp.headers['content-type'] != 'application/json':
                raise MissingKitError()

            genes = resp.json()
            for gene in genes:
                yield gene
            offset += 100
    
    def genome(self):
        for chromosome in CHROMOSOMES:
            yield from self.chromosome(chromosome)

if __name__ == '__main__':
    import json
    from creds import aka_email, aka_pass
    m23 = MeAnd23()
    m23.login(aka_email, aka_pass)
    profiles = m23.profiles()
    profiles_with_kit = []
    for profile in profiles:
        try:
            m23.use_profile(profile)
            m23.chromosome(1)
            profiles_with_kit.append(profile)
        except MissingKitError:
            pass

    for profile in profiles_with_kit:
        m23.use_profile(profile)
        for gene in m23.genome():
            print(json.dumps(gene))
