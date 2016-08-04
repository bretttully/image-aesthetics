# coding: utf-8
# Copyright 2016 Brett Tully. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""
A set of functions for scraping data from the www.dpchallenge.com website.
This is an awesome community of photographers who submit and review images.
The community have built a great database for training ML algorithms, and
here I am following the lead of http://www.lucamarchesotti.com/:
'AVA: A Large-Scale Database for Aesthetic Visual Analysis'
Please respect the copyright of these images and only use this for research
or personal learning purposes.
"""
from __future__ import print_function
import re
import os
import pandas as pd
import sys
if sys.version_info < (3,):
    import urllib2 as URL
else:
    import urllib.request as URL

USE_PARALLEL = True
if USE_PARALLEL:
    import multiprocessing as mp
    PROCESSOR_COUNT = mp.cpu_count()


BASE_DIR = os.path.dirname(__file__)
IMAGE_DIR = os.path.join(BASE_DIR, 'images')
HDF_FILENAME = os.path.join(BASE_DIR, 'DigitalPhotographyChallenge.h5')


class DPChallengeObject(object):
    __slots__ = ('id',)

    def __init__(self, _id):
        for sl in self.__slots__:
            self.__setattr__(sl, None)
        self.id = int(_id)

    def __cmp__(self, other):
        return self.id.__cmp__(other.id)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self.id)

    def __str__(self):
        s = list()
        s.append(self.__class__.__name__)
        for sl in self.__slots__:
            s.append('\t{}: {}'.format(sl, self.__getattribute__(sl)))
        return '\n'.join(s)

    def valid(self):
        for sl in self.__slots__:
            if self.__getattribute__(sl) is None:
                return False
        return True


class Challenge(DPChallengeObject):
    __slots__ = ('id',
                 'title',
                 'images')

    def __init__(self, _id):
        super(Challenge, self).__init__(_id)

    def _page_url(self, page):
        return 'http://www.dpchallenge.com/challenge_results.php?CHALLENGE_ID={}&page={}'.format(self.id, page)

    def scrape(self):
        print('Processing challenge: {}'.format(self.id))
        images = list()
        page_number = 1
        while True:
            challenge_url = self._page_url(page_number)
            try:
                response = URL.urlopen(challenge_url)
            except URL.URLError:
                break

            html = response.read()
            imgs = re.compile('image.php\?IMAGE_ID=(.*)" class.*>').findall(html)
            if len(imgs) == 0:
                break
            images.extend(imgs)

            if page_number == 1:
                try:
                    self.title = re.compile('<title>(.*) Challenge Results</title>').findall(html)[0]
                except IndexError as e:
                    print(e)
                    return

            page_number += 1

        if len(images) > 0:
            self.images = sorted([int(i) for i in images])


class Image(DPChallengeObject):
    __slots__ = ('id',
                 'url',
                 'challenge',
                 'rating',
                 'votes')

    def __init__(self, _id):
        super(Image, self).__init__(_id)

    @classmethod
    def filename(cls, _id):
        return os.path.join(IMAGE_DIR, '{}.jpg'.format(_id))

    @classmethod
    def download_image(cls, url, _id):
        filename = cls.filename(_id)
        print('Downloading image file: {}'.format(filename))
        try:
            response = URL.urlopen(url)
            with open(filename, 'wb') as f:
                f.write(response.read())

        except URL.URLError as e:
            print(e)
            return

    def scrape(self):
        print('Processing image: {}'.format(self.id))
        try:
            image_url = 'http://www.dpchallenge.com/image.php?IMAGE_ID={}'.format(self.id)
            response = URL.urlopen(image_url)
            html = response.read()

            url_fmt = 'http.*Copyrighted_Image_Reuse_Prohibited_{}.jpg'
            self.url = re.compile(url_fmt.format(self.id)).findall(html)[0]

            self.challenge = int(re.compile('challenge_results_rss.php\?CHALLENGE_ID=(\d+)').findall(html)[0])
            self.rating = float(re.compile('<b>Avg \(all users\):</b>\s*([+-]?[\d\.]+)<br>').findall(html)[0])
            self.votes = int(re.compile('<b>Votes:</b>\s*([+-]?[\d\.]+)<br>').findall(html)[0])

        except (URL.URLError, ValueError, IndexError) as e:
            print(e)
            return


def _scrape_challenge(challenge_id):
    challenge = Challenge(challenge_id)
    challenge.scrape()
    return challenge


def _scrape_image(image_id):
    image = Image(image_id)
    image.scrape()
    return image


def create_databases():
    # ---
    # scrape the challenge pages and get all of the image ids
    maximum_challenge_id = 3000
    if USE_PARALLEL:
        pool = mp.Pool(processes=PROCESSOR_COUNT)
        challenges = pool.map(_scrape_challenge, range(maximum_challenge_id))
    else:
        challenges = [_scrape_challenge(_id) for _id in range(maximum_challenge_id)]
    challenges = [c for c in challenges if c.valid()]

    # ---
    # save these to pandas
    challenge_meta_dict = dict()
    challenge_meta_dict['challenge_id'] = list()
    challenge_meta_dict['challenge_title'] = list()
    for challenge in challenges:
        challenge_meta_dict['challenge_id'].append(challenge.id)
        challenge_meta_dict['challenge_title'].append(challenge.title)
    with pd.HDFStore(HDF_FILENAME) as store:
        store['challenges'] = pd.DataFrame(challenge_meta_dict,
                                           index=challenge_meta_dict['challenge_id'])

    # ---
    # scrape the image pages to get the image meta data
    image_ids = list()
    for challenge in challenges:
        assert isinstance(challenge, Challenge)
        image_ids.extend(challenge.images)
    if USE_PARALLEL:
        pool = mp.Pool(processes=PROCESSOR_COUNT)
        images = pool.map(_scrape_image, image_ids)
    else:
        images = [_scrape_image(_id) for _id in image_ids]
    images = [i for i in images if i.valid()]

    # ---
    # save these to pandas
    image_meta_dict = dict()
    image_meta_dict['image_id'] = list()
    image_meta_dict['image_url'] = list()
    image_meta_dict['challenge_id'] = list()
    image_meta_dict['rating'] = list()
    image_meta_dict['votes'] = list()
    for image in images:
        image_meta_dict['image_id'].append(image.id)
        image_meta_dict['image_url'].append(image.url)
        image_meta_dict['challenge_id'].append(image.challenge)
        image_meta_dict['rating'].append(image.rating)
        image_meta_dict['votes'].append(image.votes)

    with pd.HDFStore(HDF_FILENAME) as store:
        store['images'] = pd.DataFrame(image_meta_dict,
                                       index=image_meta_dict['image_id'])


def _download_image(image):
    assert isinstance(image, Image)
    Image.download_image(image.url, image.id)


def download_images():
    # ---
    # read the hdf 5 file
    df = pd.read_hdf(HDF_FILENAME, key='images')
    images = list()
    for index, row in df.iterrows():
        if os.path.exists(Image.filename(index)):
            continue
        img = Image(index)
        img.url = row['image_url']
        images.append(img)

    # ---
    # download the images to disk
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)
    if USE_PARALLEL:
        pool = mp.Pool(processes=PROCESSOR_COUNT)
        pool.map(_download_image, images)
    else:
        for img in images:
            _download_image(img)


def normalise_rating():
    # ---
    # read the hdf 5 file
    df = pd.read_hdf(HDF_FILENAME, key='images')
    rating = df['rating']
    r_max = rating.max()
    r_min = rating.min()
    # normalise rating to be in range [1, 5]
    df['category'] = rating.apply(lambda x: min(5, 1 + int(5.0 * (x - r_min) / (r_max - r_min))))
    import matplotlib.pyplot as plt
    df['category'].hist()
    plt.show()

    with pd.HDFStore(HDF_FILENAME) as store:
        store['images'] = df


if __name__ == '__main__':
    create_databases()
    download_images()
    normalise_rating()
