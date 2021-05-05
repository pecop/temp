# %%
# Standard import
import sys
import time
import re
import pandas as pd
import numpy as np
from datetime import datetime as dt
import os


# Third party import
import requests
from bs4 import BeautifulSoup
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    WebDriverException,
    InvalidArgumentException,
    NoSuchElementException,
    TimeoutException,
)


# Original import
from my_package.logger import logger
from my_package.scraping import (
    set_driver,
    get_with_wait,
    parse_html,
    parse_html_selenium,
    keep_open_driver
)
from my_package.spreadsheet_settings import (
    excel_save,
    set_font,
    set_border,
)


# Local import
import dotenv_settings


# Development import
from pprint import pprint


# Global
CHROME_PROFILE_PATH = dotenv_settings.CHROME_PROFILE_PATH
TOP_URL = 'https://www.mercari.com'


# 商品クラス
class Item():

    count = 0

    @classmethod
    def countup(cls):
        cls.count += 1

    def __init__(self, url):
        self.countup()
        self.url = url
        self.item_info = {
            '商品タイトル': '',
            '商品URL': url,
            '販売価格': 0,
            '出品者名': '',
            '出品者評価数(like)': 0,
            '出品者評価数(bad)': 0,
            '出品時刻': '',
            '売却時刻': '',
            '出品時刻(UNIX)': '',
            '売却時刻(UNIX)': '',
            '売却時刻-出品時刻(hours)': 0,
        }

    # 必要情報を抽出
    def fetch_info(self, driver):

        # 不動産ジャパンから必要情報を抽出
        get_with_wait(driver, self.url, isWait=True)
        wait = WebDriverWait(driver, timeout=10)
        wait_selector = 'table[class="item-detail-table"] tr:nth-of-type(11)'
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector)))
        except TimeoutException as err:
            logger.debug(err)
        soup = parse_html_selenium(driver)

        self.fetch_title(soup)
        self.fetch_price(soup)
        self.fetch_table(soup)
    
    def fetch_title(self, soup):

        title = soup.select_one('h1.item-name').get_text(strip=True)
        self.item_info['商品タイトル'] = title
        logger.debug(f'商品タイトル：{title}')
    
    def fetch_price(self, soup):

        price = soup.select_one('span.item-price.bold').get_text(strip=True)
        pattern = '(\d)*(,)*(\d)*(,)*(\d)+'
        price = re.search(pattern, price).group()
        price = price.replace(',', '')
        self.item_info['販売価格'] = price
        logger.debug(f'販売価格：{price}円')

    def fetch_table(self, soup):

        ths = soup.select('table.item-detail-table th')
        tds = soup.select('table.item-detail-table td')

        table_dict = {}
        for th, td in zip(ths, tds):
            table_dict[th.get_text(strip=True)] = td

        self.fetch_seller(table_dict['出品者'])
        self.fetch_time(table_dict['出品日時'], table_dict['更新日時'])
    
    def fetch_seller(self, seller):

        seller_name = seller.select_one('a').get_text(strip=True)
        self.item_info['出品者名'] = seller_name
        ratings = seller.select('div.item-user-ratings span')
        like = int(ratings[0].get_text(strip=True))
        bad = int(ratings[1].get_text(strip=True))
        self.item_info['出品者評価数(like)'] = like
        self.item_info['出品者評価数(bad)'] = bad

        logger.debug(f'出品者名：{seller_name}')
        logger.debug(f'Like：{like}')
        logger.debug(f'Bad：{bad}')
    
    def fetch_time(self, time1, time2):

        created = self.item_info['出品時刻'] = time1.text
        updated = self.item_info['売却時刻'] = time2.text
        created_unix = dt.strptime(created, '%Y/%m/%d %H:%M:%S').timestamp()
        updated_unix = dt.strptime(updated, '%Y/%m/%d %H:%M:%S').timestamp()
        self.item_info['出品時刻(UNIX)'] = created_unix
        self.item_info['売却時刻(UNIX)'] = updated_unix
        delta = self.item_info['売却時刻-出品時刻(hours)'] = round((updated_unix - created_unix) / 3600, 2)
        logger.debug(f'出品時刻：{created}, UNIX：{created_unix}')
        logger.debug(f'売却時刻：{updated}, UNIX：{updated_unix}')
        logger.debug(f'売却時刻-出品時刻(hours)：{delta}')

# %%

def main():

    url = 'https://www.mercari.com/jp/search/?sort_order=&keyword=%E3%83%8A%E3%82%A4%E3%82%AD&category_root=2&category_child=&brand_name=&brand_id=&size_group=&price_min=3000&price_max=5000&item_condition_id%5B1%5D=1&status_trading_sold_out=1'

    # driver = set_driver(isHeadless=False, isManager=True, isExtension=True, profile_path=CHROME_PROFILE_PATH)  # Seleniumドライバ設定
    driver = set_driver(isHeadless=False, isManager=False, isExtension=True, profile_path=CHROME_PROFILE_PATH)  # Seleniumドライバ設定

    if driver is None:  # ドライバの設定が不正の場合はNoneが返ってくるので、システム終了
        sys.exit()

    get_with_wait(driver, url, isWait=True)  # 待機付きページ移動
    soup = parse_html_selenium(driver)

    links = []
    link_nodes = soup.select('section.items-box a')

    for node in link_nodes:
        links.append(TOP_URL + node.attrs['href'])

    items = []

    start = dt.now().strftime('%Y%m%d_%H%M%S')

    for link in links:
        logger.debug(f'No.{Item.count + 1}')
        item = Item(link)
        items.append(item)
        item.fetch_info(driver)
        logger.debug('')

        break

    end = dt.now().strftime('%Y%m%d_%H%M%S')
    logger.debug(f'開始時間：{start}, 終了時間：{end}')

    # ファイル名設定
    # filename = dt.now().strftime('%Y%m%d_%H%M') + '_mercari_demo' + '.xlsx'
    # ********************追加：ここから********************
    name = dt.now().strftime('%Y%m%d_%H%M') + '_mercari_demo' + '.xlsx'
    
    # ".exe"ファイルの場合
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)

        #".app"の場合（dist以外の任意のディレクトリでも実行可能にする）
        if '.app' in base_path:
            idx = base_path.find('.app') 
            base_path = base_path[:idx]
            idx = base_path.rfind('/')
            base_path = base_path[:idx]

    # スクリプトファイルの場合（".py"、".pyw"など）
    elif __file__:
        base_path = os.getcwd()
    
    filename = base_path + '/' + name
    # ********************追加：ここまで********************

    keys = items[0].item_info  # 取得情報のキー取得

    # 各取得情報の空リスト作成
    values = []
    for i in range(len(keys)):
        values.append([])
    item_dict = dict(zip(keys, values))

    # Itemの情報を辞書内のリストに追加
    for item in items:
        for k, v in item.item_info.items():
                item_dict[k].append(v)

    df = pd.DataFrame(item_dict)  # ディクショナリをDataFrameに変換
    df.index += 1  # indexを1始まりに設定
    excel_save(df, filename)  # Excelファイル保存
    set_font(filename)  # フォントをメイリオに設定
    set_border(filename)  # ボーダー追加

    keep_open_driver(driver)

if __name__ == "__main__":
    main()


# %%