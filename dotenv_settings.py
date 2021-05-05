import os
import sys
from os.path import join, dirname
from dotenv import load_dotenv

# if getattr(sys, 'frozen', False):
#     directory_path = os.path.dirname(os.path.abspath(sys.executable))
# else:
#     directory_path = os.path.dirname(os.path.abspath(__file__))
# ********************追加：ここから********************
# ".exe"ファイルの場合
if getattr(sys, 'frozen', False):
    directory_path = os.path.dirname(sys.executable)

    #".app"の場合（dist以外の任意のディレクトリでも実行可能にする）
    if '.app' in directory_path:
        idx = directory_path.find('.app') 
        directory_path = directory_path[:idx]
        idx = directory_path.rfind('/')
        directory_path = directory_path[:idx]

# スクリプトファイルの場合（".py"、".pyw"など）
elif __file__:
    directory_path = os.getcwd()
# ********************追加：ここまで********************

dotenv_path = join(directory_path, '.env')
load_dotenv(dotenv_path)

CHROME_PROFILE_PATH = os.environ.get('CHROME_PROFILE_PATH')
