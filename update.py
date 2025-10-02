# 每日更新脚本入口
import subprocess
import os

# 执行更新
python_file = os.path.join(os.path.dirname(__file__), 'python_script','update.py')
subprocess.call(f'D:\software\anaconda\python.exe {python_file}',working_dir='.')

# 构建静态网页

