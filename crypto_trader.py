# -*- coding: utf-8 -*-
# polymarket_v1.0.0
import platform
import tkinter as tk
from tkinter import ttk, messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
import json
import threading
import time
import os
import pytesseract
from screeninfo import get_monitors
import logging
from datetime import datetime, timezone, timedelta
import re
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import pyautogui
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import socket
import sys
import logging
from xpath_config import XPathConfig
from threading import Thread

class Logger:
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # 创建logs目录（如果不存在）
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        # 设置日志文件名（使用当前日期）
        log_filename = f"logs/{datetime.now().strftime('%Y%m%d')}.log"
        
        # 创建文件处理器
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        
        # 创建格式器
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加处理器到logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def debug(self, message):
        self.logger.debug(message)
    
    def info(self, message):
        self.logger.info(message)
    
    def warning(self, message):
        self.logger.warning(message)
    
    def error(self, message):
        self.logger.error(message)
    
    def critical(self, message):
        self.logger.critical(message)

class CryptoTrader:
    def __init__(self):
        super().__init__()
        self.logger = Logger('poly')
        self.driver = None
        self.running = False
        self.trading = False
        self.login_running = False
        # 添加交易状态
        self.stop_auto_find_running = False
        self.start_login_monitoring_running = False
        self.url_monitoring_running = False
        self.refresh_page_running = False
        self.start_auto_find_coin_running = False

        self.retry_count = 3
        self.retry_interval = 5
        # 添加交易次数计数器
        self.trade_count = 0
        self.sell_count = 0  # 添加卖出计数器
        self.refresh_interval = 600000  # 10分钟 = 600000毫秒
        # 添加定时器
        self.refresh_page_timer = None  # 用于存储定时器ID
        self.url_check_timer = None
        self.auto_find_coin_timer = None

        # 添加URL and refresh_page监控锁
        self.url_monitoring_lock = threading.Lock()
        self.refresh_page_lock = threading.Lock()

        self.default_target_price = 0.54
        self._amounts_logged = False
        # 在初始化部分添加
        self.stop_event = threading.Event()
        # 初始化金额属性
        for i in range(1, 4):  # 1到3
            setattr(self, f'yes{i}_amount', 0.0)
            setattr(self, f'no{i}_amount', 0.0)

        try:
            self.config = self.load_config()
            self.setup_gui()
            
            # 获取屏幕尺寸并设置窗口位置
            self.root.update_idletasks()  # 确保窗口尺寸已计算
            window_width = self.root.winfo_width()
            screen_height = self.root.winfo_screenheight()
            
            # 设置窗口位置在屏幕最左边
            self.root.geometry(f"{window_width}x{screen_height}+0+0")
        except Exception as e:
            self.logger.error(f"初始化失败: {str(e)}")
            messagebox.showerror("错误", "程序初始化失败，请检查日志文件")
            sys.exit(1)

        # 打印启动参数
        self.logger.info(f"CryptoTrader初始化,启动参数: {sys.argv}")
    
        # 检查是否是重启
        self.is_restart = '--restart' in sys.argv
        
        # 如果是重启,延迟2秒后自动点击开始监控
        if self.is_restart:
            self.logger.info("检测到重启模式,安排自动点击开始按钮！")
            self.root.after(10000, self.auto_start_monitor)
      
        # 添加登录状态监控定时器
        self.login_check_timer = None

    def load_config(self):
        """加载配置文件，保持默认格式"""
        try:
            # 默认配置
            default_config = {
                'website': {'url': ''},
                'trading': {
                    'Yes1': {'target_price': 0.0, 'amount': 0.0},
                    'Yes2': {'target_price': 0.0, 'amount': 0.0},
                    'Yes3': {'target_price': 0.0, 'amount': 0.0},
                    'Yes4': {'target_price': 0.0, 'amount': 0.0},
                    'Yes5': {'target_price': 0.0, 'amount': 0.0},

                    'No1': {'target_price': 0.0, 'amount': 0.0},
                    'No2': {'target_price': 0.0, 'amount': 0.0},
                    'No3': {'target_price': 0.0, 'amount': 0.0},
                    'No4': {'target_price': 0.0, 'amount': 0.0},
                    'No5': {'target_price': 0.0, 'amount': 0.0}
                },
                'url_history': []
            }
            
            try:
                # 尝试读取现有配置
                with open('config.json', 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    self.logger.info("成功加载配置文件")
                    
                    # 合并配置
                    for key in default_config:
                        if key not in saved_config:
                            saved_config[key] = default_config[key]
                        elif isinstance(default_config[key], dict):
                            for sub_key in default_config[key]:
                                if sub_key not in saved_config[key]:
                                    saved_config[key][sub_key] = default_config[key][sub_key]
                    return saved_config
            except FileNotFoundError:
                self.logger.warning("配置文件不存在，创建默认配置")
                with open('config.json', 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4, ensure_ascii=False)
                return default_config
            except json.JSONDecodeError:
                self.logger.error("配置文件格式错误，使用默认配置")
                with open('config.json', 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4, ensure_ascii=False)
                return default_config
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {str(e)}")
            raise
    
    def save_config(self):
        """保存配置到文件,保持JSON格式化"""
        try:
            for position, frame in [('Yes', self.yes_frame), ('No', self.no_frame)]:
                # 精确获取目标价格和金额的输入框
                entries = [
                    w for w in frame.winfo_children() 
                    if isinstance(w, ttk.Entry) and "price" in str(w).lower()
                ]
                amount_entries = [
                    w for w in frame.winfo_children()
                    if isinstance(w, ttk.Entry) and "amount" in str(w).lower()
                ]

                # 添加类型转换保护
                try:
                    target_price = float(entries[0].get().strip() or '0.0') if entries else 0.0
                except ValueError as e:
                    self.logger.error(f"价格转换失败: {e}, 使用默认值0.0")
                    target_price = 0.0

                try:
                    amount = float(amount_entries[0].get().strip() or '0.0') if amount_entries else 0.0
                except ValueError as e:
                    self.logger.error(f"金额转换失败: {e}, 使用默认值0.0")
                    amount = 0.0

                # 使用正确的配置键格式
                config_key = f"{position}0"  # 改为Yes1/No1
                self.config['trading'][config_key]['target_price'] = target_price
                self.config['trading'][config_key]['amount'] = amount

            # 处理网站地址历史记录
            current_url = self.url_entry.get().strip()
            if current_url:
                if 'url_history' not in self.config:
                    self.config['url_history'] = []
                
                # 清空历史记录
                self.config['url_history'].clear()
                # 只保留当前URL
                self.config['url_history'].insert(0, current_url)
                # 确保最多保留1条
                self.config['url_history'] = self.config['url_history'][:1]
                self.url_entry['values'] = self.config['url_history']
            
            # 保存配置到文件，使用indent=4确保格式化
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(self.config, f)
                
        except Exception as e:
            self.logger.error(f"保存配置失败: {str(e)}")
            raise

    """从这里开始设置 GUI 直到 784 行"""
    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("Polymarket automatic trading")
        # 创建主滚动框架
        main_canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        scrollable_frame = ttk.Frame(main_canvas)
        # 配置滚动区域
        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        # 在 Canvas 中创建窗口
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)
        # 简化的滚动事件处理
        def _on_mousewheel(event):
            try:
                if platform.system() == 'Linux':
                    if event.num == 4:
                        main_canvas.yview_scroll(-1, "units")
                    elif event.num == 5:
                        main_canvas.yview_scroll(1, "units")
                elif platform.system() == 'Darwin':
                    main_canvas.yview_scroll(-int(event.delta), "units")
                else:  # Windows
                    main_canvas.yview_scroll(-int(event.delta/120), "units")
            except Exception as e:
                self.logger.error(f"滚动事件处理错误: {str(e)}")
        # 绑定滚动事件
        if platform.system() == 'Linux':
            main_canvas.bind_all("<Button-4>", _on_mousewheel)
            main_canvas.bind_all("<Button-5>", _on_mousewheel)
        else:
            main_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        # 添加简化的键盘滚动支持
        def _on_arrow_key(event):
            try:
                if event.keysym == 'Up':
                    main_canvas.yview_scroll(-1, "units")
                elif event.keysym == 'Down':
                    main_canvas.yview_scroll(1, "units")
            except Exception as e:
                self.logger.error(f"键盘滚动事件处理错误: {str(e)}")
        # 绑定方向键
        main_canvas.bind_all("<Up>", _on_arrow_key)
        main_canvas.bind_all("<Down>", _on_arrow_key)
        
        # 放置滚动组件
        main_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        """创建按钮和输入框样式"""
        style = ttk.Style()
        style.configure('Red.TButton', foreground='red', font=('TkDefaultFont', 14, 'bold'))
        style.configure('Black.TButton', foreground='black', font=('TkDefaultFont', 14, 'normal'))
        style.configure('Red.TEntry', foreground='red', font=('TkDefaultFont', 14, 'normal'))
        style.configure('Blue.TButton', foreground='blue', font=('TkDefaultFont', 14, 'normal'))
        style.configure('Blue.TLabel', foreground='blue', font=('TkDefaultFont', 14, 'normal'))
        style.configure('Red.TLabel', foreground='red', font=('TkDefaultFont', 14, 'normal'))
        style.configure('Red.TLabelframe.Label', foreground='red')  # 设置标签文本颜色为红色
        style.configure('Black.TLabel', foreground='black', font=('TkDefaultFont', 14, 'normal'))
        style.configure('Warning.TLabelframe.Label', font=('TkDefaultFont', 14, 'bold'),foreground='red', anchor='center', justify='center')
        
        # 金额设置框架
        amount_settings_frame = ttk.LabelFrame(scrollable_frame, text="Do't be greedy, or you will lose money!", padding=(2, 5), style='Warning.TLabelframe')
        amount_settings_frame.pack(fill="x", padx=5, pady=5)

        # 创建一个Frame来水平排列标题和警告
        title_frame = ttk.Frame(amount_settings_frame)
        title_frame.pack(fill="x", padx=5, pady=5)

        # 添加标题和红色警告文本在同一行
        ttk.Label(title_frame, 
                text="Rule: Do not intervene in the automatic program!",
                foreground='red',
                font=('TkDefaultFont', 14, 'bold')).pack(side=tk.RIGHT, expand=True)

        # 创建金额设置容器的内部框架
        settings_container = ttk.Frame(amount_settings_frame)
        settings_container.pack(fill=tk.X, anchor='w')
        
        # 创建两个独立的Frame
        amount_frame = ttk.Frame(settings_container)
        amount_frame.grid(row=0, column=0, sticky='w')
        trades_frame = ttk.Frame(settings_container)
        trades_frame.grid(row=1, column=0, sticky='w')

        # 初始金额等输入框放在amount_frame中
        initial_frame = ttk.Frame(amount_frame)
        initial_frame.pack(side=tk.LEFT, padx=2)
        ttk.Label(initial_frame, text="Initial:").pack(side=tk.LEFT)
        self.initial_amount_entry = ttk.Entry(initial_frame, width=2)
        self.initial_amount_entry.pack(side=tk.LEFT)
        self.initial_amount_entry.insert(0, "6")
        
        # 反水一次设置
        first_frame = ttk.Frame(amount_frame)
        first_frame.pack(side=tk.LEFT, padx=2)
        ttk.Label(first_frame, text="Turn-1:").pack(side=tk.LEFT)
        self.first_rebound_entry = ttk.Entry(first_frame, width=3)
        self.first_rebound_entry.pack(side=tk.LEFT)
        self.first_rebound_entry.insert(0, "300")
        
        # 反水N次设置
        n_frame = ttk.Frame(amount_frame)
        n_frame.pack(side=tk.LEFT, padx=2)
        ttk.Label(n_frame, text="Turn-N:").pack(side=tk.LEFT)
        self.n_rebound_entry = ttk.Entry(n_frame, width=3)
        self.n_rebound_entry.pack(side=tk.LEFT)
        self.n_rebound_entry.insert(0, "160")

        # 利润率设置
        profit_frame = ttk.Frame(amount_frame)
        profit_frame.pack(side=tk.LEFT, padx=2)
        ttk.Label(profit_frame, text="Margin:").pack(side=tk.LEFT)
        self.profit_rate_entry = ttk.Entry(profit_frame, width=2)
        self.profit_rate_entry.pack(side=tk.LEFT)
        self.profit_rate_entry.insert(0, "6")

        # 翻倍周数
        weeks_frame = ttk.Frame(amount_frame)
        weeks_frame.pack(side=tk.LEFT, padx=2)
        self.doubling_weeks_entry = ttk.Entry(weeks_frame, width=2, style='Red.TEntry')
        self.doubling_weeks_entry.pack(side=tk.LEFT)
        self.doubling_weeks_entry.insert(0, "15")
        ttk.Label(weeks_frame, text="Double", style='Red.TLabel').pack(side=tk.LEFT)

        # 交易币种按钮放在trades_frame中
        ttk.Label(trades_frame, text="Cryptos:", style='Black.TLabel').pack(side=tk.LEFT, padx=(2,2))
        buttons_frame = ttk.Frame(trades_frame)
        buttons_frame.pack(side=tk.LEFT, padx=(0,0))

        # 次数按钮
        self.trade_buttons = {}  # 保存按钮引用

        # 添加搜索BTC周链接按钮
        self.btc_button = ttk.Button(buttons_frame, text="BTC", 
                                         command=lambda: self.find_weekly_url('BTC'), width=3,
                                         style='Blue.TButton')
        self.btc_button.grid(row=1, column=0, padx=2, pady=3)

        # 添加搜索ETH周链接按钮
        self.eth_button = ttk.Button(buttons_frame, text="ETH", 
                                         command=lambda: self.find_weekly_url('ETH'), width=3,
                                         style='Blue.TButton')
        self.eth_button.grid(row=1, column=1, padx=2, pady=3)

        # 添加搜索SOLANA周链接按钮
        self.solana_button = ttk.Button(buttons_frame, text="SOL", 
                                         command=lambda: self.find_weekly_url('SOLANA'), width=3,
                                         style='Blue.TButton')
        self.solana_button.grid(row=1, column=2, padx=2, pady=3)

        # 添加搜索XRP周链接按钮
        self.xrp_button = ttk.Button(buttons_frame, text="XRP", 
                                         command=lambda: self.find_weekly_url('XRP'), width=3,
                                         style='Blue.TButton')
        self.xrp_button.grid(row=1, column=3, padx=2, pady=3)

        # 配置列权重使输入框均匀分布
        for i in range(8):
            settings_container.grid_columnconfigure(i, weight=1)

        """设置窗口大小和位置"""
        window_width = 470
        window_height = 800
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f'{window_width}x{window_height}+{x}+{y}')
        
        # 监控网站配置
        url_frame = ttk.LabelFrame(scrollable_frame, text="Monitoring-Website-Configuration", padding=(2, 2))
        url_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(url_frame, text="WEB:", font=('Arial', 10)).grid(row=0, column=0, padx=5, pady=5)
        
        # 创建下拉列和输入框组合控件
        self.url_entry = ttk.Combobox(url_frame, width=40)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # 从配置文件加载历史记录
        if 'url_history' not in self.config:
            self.config['url_history'] = []
        self.url_entry['values'] = self.config['url_history']
        
        # 如果有当前URL，设置为默认值
        current_url = self.config.get('website', {}).get('url', '')
        if current_url:
            self.url_entry.set(current_url)
        
        # 控制按钮区域
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill="x", padx=5, pady=5)
        
        # 开始和停止按钮
        self.start_button = ttk.Button(button_frame, text="Start", 
                                          command=self.start_monitoring, width=3.5,
                                          style='Black.TButton')  # 默认使用黑色文字
        self.start_button.pack(side=tk.LEFT, padx=1)
        
        
        self.stop_button = ttk.Button(button_frame, text="Stop", 
                                     command=self.stop_monitoring, width=3.5,
                                     style='Black.TButton')  # 默认使用黑色文字
        self.stop_button.pack(side=tk.LEFT, padx=1)
        self.stop_button['state'] = 'disabled'
        
        # 设置金额按钮
        self.set_amount_button = ttk.Button(button_frame, text="Set-Amount", 
                                             command=self.set_yes_no_cash, width=12,
                                             style='Black.TButton')  # 默认使用黑色文字
        self.set_amount_button.pack(side=tk.LEFT, padx=1)
        self.set_amount_button['state'] = 'disabled'  # 初始禁用

        # 添加价格按钮
        prices = ['0.54', '0.55']
        for price in prices:
            btn = ttk.Button(
                button_frame, 
                text=price,
                width=3.5,
                command=lambda p=price: self.set_default_price(p),
                style='Red.TButton' if price == '0.54' else 'Black.TButton'
            )
            btn.pack(side=tk.LEFT, padx=2)
        
        # 交易币对显示区域
        pair_frame = ttk.Frame(scrollable_frame)
        pair_frame.pack(fill="x", padx=2, pady=5)
        
        # 添加交易币对显示区域
        pair_container = ttk.Frame(pair_frame)
        pair_container.pack(anchor="center")
        
        # 交易币种及日期，颜色为蓝色
        ttk.Label(pair_container, text="Crypto:", 
                 font=('Arial', 14), foreground='blue').pack(side=tk.LEFT, padx=5)
        self.trading_pair_label = ttk.Label(pair_container, text="--", 
                                        font=('Arial', 16, 'bold'), foreground='blue')
        self.trading_pair_label.pack(side=tk.LEFT, padx=5)
        
        # 修改实时价格显示区域
        price_frame = ttk.LabelFrame(scrollable_frame, text="Price", padding=(5, 5))
        price_frame.pack(padx=5, pady=5, fill="x")
        
        # 创建一个框架来水平排列所有价格信息
        prices_container = ttk.Frame(price_frame)
        prices_container.pack(expand=True)  # 添加expand=True使容器居中
        
        # Yes实时价格显示
        self.yes_price_label = ttk.Label(prices_container, text="Yes: waiting...", 
                                        font=('Arial', 18), foreground='#9370DB')
        self.yes_price_label.pack(side=tk.LEFT, padx=18)
        
        # No实时价格显示
        self.no_price_label = ttk.Label(prices_container, text="No: waiting...", 
                                       font=('Arial', 18), foreground='#9370DB')
        self.no_price_label.pack(side=tk.LEFT, padx=18)
        
        # 最后更新时间 - 靠右下对齐
        self.last_update_label = ttk.Label(price_frame, text="Last-Update: --", 
                                          font=('Arial', 2))
        self.last_update_label.pack(side=tk.LEFT, anchor='se', padx=5)
        
        # 修改实时资金显示区域
        balance_frame = ttk.LabelFrame(scrollable_frame, text="Balance", padding=(5, 5))
        balance_frame.pack(padx=5, pady=5, fill="x")
        
        # 创建一个框架来水平排列所有资金信息
        balance_container = ttk.Frame(balance_frame)
        balance_container.pack(expand=True)  # 添加expand=True使容器居中
        
        # Portfolio显示
        self.portfolio_label = ttk.Label(balance_container, text="Portfolio: waiting...", 
                                        font=('Arial', 18), foreground='#9370DB') # 修改为绿色
        self.portfolio_label.pack(side=tk.LEFT, padx=18)
        
        # Cash显示
        self.cash_label = ttk.Label(balance_container, text="Cash: waiting...", 
                                   font=('Arial', 18), foreground='#9370DB') # 修改为绿色
        self.cash_label.pack(side=tk.LEFT, padx=18)
        
        # 最后更新时间 - 靠右下对齐
        self.balance_update_label = ttk.Label(balance_frame, text="Last-Update: --", 
                                           font=('Arial', 2))
        self.balance_update_label.pack(side=tk.LEFT, anchor='se', padx=5)
        
        # 创建Yes/No
        config_frame = ttk.Frame(scrollable_frame)
        config_frame.pack(fill="x", padx=2, pady=5)
        
        # 左右分栏显示Yes/No配置
        # YES 区域配置
        self.yes_frame = ttk.LabelFrame(config_frame, text="Yes config", padding=(2, 3))
        self.yes_frame.grid(row=0, column=0, padx=2, sticky="ew")
        config_frame.grid_columnconfigure(0, weight=1)

        # No 配置区域
        self.no_frame = ttk.LabelFrame(config_frame, text="No config", padding=(2, 3))
        self.no_frame.grid(row=0, column=1, padx=2, sticky="ew")
        config_frame.grid_columnconfigure(1, weight=1)
        
        # YES1 价格
        ttk.Label(self.yes_frame, text="Yes1 Price($):", font=('Arial', 12)).grid(row=0, column=0, padx=2, pady=5)
        self.yes1_price_entry = ttk.Entry(self.yes_frame, width=12)
        self.yes1_price_entry.insert(0, str(self.config['trading']['Yes1']['target_price']))
        self.yes1_price_entry.grid(row=0, column=1, padx=2, pady=5, sticky="ew")

        # yes2 价格
        ttk.Label(self.yes_frame, text="Yes2 Price($):", font=('Arial', 12)).grid(row=2, column=0, padx=2, pady=5)
        self.yes2_price_entry = ttk.Entry(self.yes_frame, width=12)  # 添加self
        self.yes2_price_entry.delete(0, tk.END)
        self.yes2_price_entry.insert(0, "0.00")
        self.yes2_price_entry.grid(row=2, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # yes3 价格
        ttk.Label(self.yes_frame, text="Yes3 Price($):", font=('Arial', 12)).grid(row=4, column=0, padx=2, pady=5)
        self.yes3_price_entry = ttk.Entry(self.yes_frame, width=12)  # 添加self
        self.yes3_price_entry.delete(0, tk.END)
        self.yes3_price_entry.insert(0, "0.00")
        self.yes3_price_entry.grid(row=4, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # yes4 价格
        ttk.Label(self.yes_frame, text="Yes4 Price($):", font=('Arial', 12)).grid(row=6, column=0, padx=2, pady=5)
        self.yes4_price_entry = ttk.Entry(self.yes_frame, width=12)  # 添加self
        self.yes4_price_entry.delete(0, tk.END)
        self.yes4_price_entry.insert(0, "0.00")
        self.yes4_price_entry.grid(row=6, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # yes5 价格
        ttk.Label(self.yes_frame, text="Yes5 Price($):", font=('Arial', 12)).grid(row=8, column=0, padx=2, pady=5)
        self.yes5_price_entry = ttk.Entry(self.yes_frame, width=12)  # 添加self
        self.yes5_price_entry.delete(0, tk.END)
        self.yes5_price_entry.insert(0, "0.00")
        self.yes5_price_entry.grid(row=8, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # yes1 金额
        ttk.Label(self.yes_frame, text="Yes1 Amount:", font=('Arial', 12)).grid(row=1, column=0, padx=2, pady=5)
        self.yes1_amount_entry = ttk.Entry(self.yes_frame, width=12)
        self.yes1_amount_entry.insert(0, str(self.config['trading']['Yes1']['amount']))
        self.yes1_amount_entry.grid(row=1, column=1, padx=2, pady=5, sticky="ew")

        # yes2 金额
        ttk.Label(self.yes_frame, text="Yes2 Amount:", font=('Arial', 12)).grid(row=3, column=0, padx=2, pady=5)
        self.yes2_amount_entry = ttk.Entry(self.yes_frame, width=12)  # 添加self
        self.yes2_amount_entry.insert(0, "0.0")
        self.yes2_amount_entry.grid(row=3, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # yes3 金额
        ttk.Label(self.yes_frame, text="Yes3 Amount:", font=('Arial', 12)).grid(row=5, column=0, padx=2, pady=5)
        self.yes3_amount_entry = ttk.Entry(self.yes_frame, width=12)  # 添加self
        self.yes3_amount_entry.insert(0, "0.0")
        self.yes3_amount_entry.grid(row=5, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # yes4 金额
        ttk.Label(self.yes_frame, text="Yes4 Amount:", font=('Arial', 12)).grid(row=7, column=0, padx=2, pady=5)
        self.yes4_amount_entry = ttk.Entry(self.yes_frame, width=12)  # 添加self
        self.yes4_amount_entry.insert(0, "0.0")
        self.yes4_amount_entry.grid(row=7, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # No1 价格
        ttk.Label(self.no_frame, text="No1 Price($):", font=('Arial', 12)).grid(row=0, column=0, padx=2, pady=5)
        self.no1_price_entry = ttk.Entry(self.no_frame, width=12)
        self.no1_price_entry.insert(0, str(self.config['trading']['No1']['target_price']))
        self.no1_price_entry.grid(row=0, column=1, padx=2, pady=5, sticky="ew")

        # No2 价格
        ttk.Label(self.no_frame, text="No2 Price($):", font=('Arial', 12)).grid(row=2, column=0, padx=2, pady=5)
        self.no2_price_entry = ttk.Entry(self.no_frame, width=12)  # 添加self
        self.no2_price_entry.delete(0, tk.END)
        self.no2_price_entry.insert(0, "0.00")
        self.no2_price_entry.grid(row=2, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # No3 价格
        ttk.Label(self.no_frame, text="No3 Price($):", font=('Arial', 12)).grid(row=4, column=0, padx=2, pady=5)
        self.no3_price_entry = ttk.Entry(self.no_frame, width=12)  # 添加self
        self.no3_price_entry.delete(0, tk.END)
        self.no3_price_entry.insert(0, "0.00")
        self.no3_price_entry.grid(row=4, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # No4 价格
        ttk.Label(self.no_frame, text="No4 Price($):", font=('Arial', 12)).grid(row=6, column=0, padx=2, pady=5)
        self.no4_price_entry = ttk.Entry(self.no_frame, width=12)  # 添加self
        self.no4_price_entry.delete(0, tk.END)
        self.no4_price_entry.insert(0, "0.00")
        self.no4_price_entry.grid(row=6, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # No5 价格
        ttk.Label(self.no_frame, text="No5 Price($):", font=('Arial', 12)).grid(row=8, column=0, padx=2, pady=5)
        self.no5_price_entry = ttk.Entry(self.no_frame, width=12)  # 添加self
        self.no5_price_entry.delete(0, tk.END)
        self.no5_price_entry.insert(0, "0.00")
        self.no5_price_entry.grid(row=8, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # NO1 金额
        ttk.Label(self.no_frame, text="No1 Amount:", font=('Arial', 12)).grid(row=1, column=0, padx=2, pady=5)
        self.no1_amount_entry = ttk.Entry(self.no_frame, width=12)
        self.no1_amount_entry.insert(0, str(self.config['trading']['No1']['amount']))
        self.no1_amount_entry.grid(row=1, column=1, padx=2, pady=5, sticky="ew")

        # No2 金额
        ttk.Label(self.no_frame, text="No2 Amount:", font=('Arial', 12)).grid(row=3, column=0, padx=2, pady=5)
        self.no2_amount_entry = ttk.Entry(self.no_frame, width=12)  # 添加self
        self.no2_amount_entry.insert(0, "0.0")
        self.no2_amount_entry.grid(row=3, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # No3 金额
        ttk.Label(self.no_frame, text="No 3 Amount:", font=('Arial', 12)).grid(row=5, column=0, padx=2, pady=5)
        self.no3_amount_entry = ttk.Entry(self.no_frame, width=12)  # 添加self
        self.no3_amount_entry.insert(0, "0.0")
        self.no3_amount_entry.grid(row=5, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # No4 金额
        ttk.Label(self.no_frame, text="No4 Amount:", font=('Arial', 12)).grid(row=7, column=0, padx=2, pady=5)
        self.no4_amount_entry = ttk.Entry(self.no_frame, width=12)  # 添加self
        self.no4_amount_entry.insert(0, "0.0")
        self.no4_amount_entry.grid(row=7, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置


        # 创建买入按钮区域
        buy_frame = ttk.LabelFrame(scrollable_frame, text="Buy-Button", padding=(2, 0))
        buy_frame.pack(fill="x", padx=(0,0), pady=2)

        # 创建按钮框架
        buy_button_frame = ttk.Frame(buy_frame)
        buy_button_frame.pack(side=tk.LEFT, padx=2)  # 添加expand=True使容器居中

        # 第一行按钮
        self.buy_button = ttk.Button(buy_button_frame, text="Buy", width=8,
                                    command=self.click_buy)
        self.buy_button.grid(row=0, column=0, padx=2, pady=5)

        self.buy_yes_button = ttk.Button(buy_button_frame, text="Buy-Yes", width=8,
                                        command=self.click_buy_yes)
        self.buy_yes_button.grid(row=0, column=1, padx=2, pady=5)

        self.buy_no_button = ttk.Button(buy_button_frame, text="Buy-No", width=8,
                                       command=self.click_buy_no)
        self.buy_no_button.grid(row=0, column=2, padx=2, pady=5)

        self.buy_confirm_button = ttk.Button(buy_button_frame, text="Buy-confirm", width=8,
                                            command=self.click_buy_confirm_button)
        self.buy_confirm_button.grid(row=0, column=3, padx=2, pady=5)

        # 第二行按钮
        self.amount_yes1_button = ttk.Button(buy_button_frame, text="Amount-Y1", width=8)
        self.amount_yes1_button.bind('<Button-1>', self.click_amount)
        self.amount_yes1_button.grid(row=1, column=0, padx=2, pady=5)

        self.amount_yes2_button = ttk.Button(buy_button_frame, text="Amount-Y2", width=8)
        self.amount_yes2_button.bind('<Button-1>', self.click_amount)
        self.amount_yes2_button.grid(row=1, column=1, padx=2, pady=5)

        self.amount_yes3_button = ttk.Button(buy_button_frame, text="Amount-Y3", width=8)
        self.amount_yes3_button.bind('<Button-1>', self.click_amount)
        self.amount_yes3_button.grid(row=1, column=2, padx=2, pady=5)

        self.amount_yes4_button = ttk.Button(buy_button_frame, text="Amount-Y4", width=8)
        self.amount_yes4_button.bind('<Button-1>', self.click_amount)
        self.amount_yes4_button.grid(row=1, column=3, padx=2, pady=5)

        # 第三行
        self.amount_no1_button = ttk.Button(buy_button_frame, text="Amount-N1", width=8)
        self.amount_no1_button.bind('<Button-1>', self.click_amount)
        self.amount_no1_button.grid(row=2, column=0, padx=2, pady=5)
        
        self.amount_no2_button = ttk.Button(buy_button_frame, text="Amount-N2", width=8)
        self.amount_no2_button.bind('<Button-1>', self.click_amount)
        self.amount_no2_button.grid(row=2, column=1, padx=2, pady=5)

        self.amount_no3_button = ttk.Button(buy_button_frame, text="Amount-N3", width=8)
        self.amount_no3_button.bind('<Button-1>', self.click_amount)
        self.amount_no3_button.grid(row=2, column=2, padx=2, pady=5)

        self.amount_no4_button = ttk.Button(buy_button_frame, text="Amount-N4", width=8)
        self.amount_no4_button.bind('<Button-1>', self.click_amount)
        self.amount_no4_button.grid(row=2, column=3, padx=2, pady=5)

        
        # 配置列权重使按钮均匀分布
        for i in range(4):
            buy_button_frame.grid_columnconfigure(i, weight=1)

        # 修改卖出按钮区域
        sell_frame = ttk.LabelFrame(scrollable_frame, text="Sell-Button", padding=(10, 5))
        sell_frame.pack(fill="x", padx=2, pady=5)

        # 创建按钮框架
        button_frame = ttk.Frame(sell_frame)
        button_frame.pack(side=tk.LEFT, fill="x", padx=2, pady=5)  # 添加expand=True使容器居

        # 第一行按钮
        self.position_sell_yes_button = ttk.Button(button_frame, text="Positions-Sell-Yes", width=13,
                                                 command=self.click_position_sell_yes)
        self.position_sell_yes_button.grid(row=0, column=0, padx=2, pady=5)

        self.position_sell_no_button = ttk.Button(button_frame, text="Positions-Sell-No", width=13,
                                                command=self.click_position_sell_no)
        self.position_sell_no_button.grid(row=0, column=1, padx=2, pady=5)

        self.sell_profit_button = ttk.Button(button_frame, text="Sell-profit", width=10,
                                           command=self.click_profit_sell)
        self.sell_profit_button.grid(row=0, column=2, padx=2, pady=5)

        # 第二行按钮
        self.sell_yes_button = ttk.Button(button_frame, text="Sell-Yes", width=10,
                                        command=self.click_sell_yes)
        self.sell_yes_button.grid(row=1, column=0, padx=2, pady=5)

        self.sell_no_button = ttk.Button(button_frame, text="Sell-No", width=10,
                                       command=self.click_sell_no)
        self.sell_no_button.grid(row=1, column=1, padx=2, pady=5)

        self.restart_program_button = ttk.Button(button_frame, text="Restart", width=6,
                                                 command=self.restart_program)
        self.restart_program_button.grid(row=1, column=2, padx=2, pady=5)

        # 配置列权重使按钮均匀分布
        for i in range(4):
            button_frame.grid_columnconfigure(i, weight=1)

        # 添加状态标签 (在卖出按钮区域之后)
        self.status_label = ttk.Label(scrollable_frame, text="Status: Not running", 
                                     font=('Arial', 10, 'bold'))
        self.status_label.pack(pady=5)
        
        # 添加版权信息标签
        copyright_label = ttk.Label(scrollable_frame, text="Powered by 无为 Copyright 2024",
                                   font=('Arial', 12), foreground='gray')
        copyright_label.pack(pady=(0, 5))  # 上边距0，下距5
    """以上代码从240行到 784 行是设置 GUI 界面的"""

    """以下代码从 785 行到行是程序交易逻辑"""
    def start_monitoring(self):
        """开始监控"""
        # 直接使用当前显示的网址
        self.target_url = self.url_entry.get()
        self.logger.info(f"✅ 开始监控网址: {self.target_url}")
        
        # 启用开始按钮，启用停止按钮
        self.start_button['state'] = 'disabled'
        self.stop_button['state'] = 'normal'
            
        # 将"开始监控"文字变为红色
        self.start_button.configure(style='Red.TButton')
        # 恢复"停止监控"文字为黑色
        self.stop_button.configure(style='Black.TButton')
        # 重置交易次数计数器
        self.trade_count = 0
            
        # 启动浏览器作线程
        threading.Thread(target=self._start_browser_monitoring, args=(self.target_url,), daemon=True).start()
        """到这里代码执行到了 995 行"""

        self.running = True
        self.update_status("monitoring...")

        # 启用设置金额按钮
        self.set_amount_button['state'] = 'normal'
        # 启动页面刷新
        self.root.after(40000, self.refresh_page)
        # 启动登录状态监控
        self.root.after(2000, self.start_login_monitoring)
        # 启动URL监控
        self.root.after(30000, self.start_url_monitoring)
        # 启动自动找币
        self.root.after(180000, self.start_auto_find_coin)
    
    def _start_browser_monitoring(self, new_url):
        """在新线程中执行浏览器操作"""
        try:
            self.update_status(f"正在尝试访问: {new_url}")
            
            if not self.driver:
                chrome_options = Options()
                chrome_options.debugger_address = "127.0.0.1:9222"
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                
                try:
                    self.driver = webdriver.Chrome(options=chrome_options)
                    self.update_status("连接到浏览器")
                except Exception as e:
                    self.logger.error(f"连接浏览器失败: {str(e)}")
                    self._show_error_and_reset("无法连接Chrome浏览器,请确保已运行start_chrome.sh")
                    return
            try:
                # 在当前标签页打开URL
                self.driver.get(new_url)
                
                # 等待页面加载
                self.update_status("等待页面加载完成...")
                WebDriverWait(self.driver, 60).until(
                    lambda driver: driver.execute_script('return document.readyState') == 'complete'
                )
                
                # 验证页面加载成功
                current_url = self.driver.current_url
                self.update_status(f"成功加载网: {current_url}")
                
                # 保存配置
                if 'website' not in self.config:
                    self.config['website'] = {}
                self.config['website']['url'] = new_url
                self.save_config()
                
                # 更新交易币对显示
                try:
                    pair = re.search(r'event/([^?]+)', new_url)
                    if pair:
                        self.trading_pair_label.config(text=pair.group(1))
                    else:
                        self.trading_pair_label.config(text="无识别事件名称")
                except Exception:
                    self.trading_pair_label.config(text="解析失败")
                #  开启监控
                self.running = True
                
                # 启动监控线程
                self.monitoring_thread = threading.Thread(target=self.monitor_prices, daemon=True)
                self.monitoring_thread.start()
                self.logger.info("✅ 启动实时监控价格和资金线程")
                
            except Exception as e:
                error_msg = f"加载网站失败: {str(e)}"
                self.logger.error(error_msg)
                self._show_error_and_reset(error_msg)  
        except Exception as e:
            error_msg = f"启动监控失败: {str(e)}"
            self.logger.error(error_msg)
            self._show_error_and_reset(error_msg)

    def _show_error_and_reset(self, error_msg):
        """显示错误并置按钮状态"""
        self.update_status(error_msg)
        # 用after方法确保在线程中执行GUI操作
        self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
        self.root.after(0, lambda: self.start_button.config(state='normal'))
        self.root.after(0, lambda: self.stop_button.config(state='disabled'))
        self.running = False

    def monitor_prices(self):
        """检查价格变化"""
        try:
            # 确保浏览器连接
            if not self.driver:
                chrome_options = Options()
                chrome_options.debugger_address = "127.0.0.1:9222"
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                self.driver = webdriver.Chrome(options=chrome_options)
                self.update_status("成功连接到浏览器")
            target_url = self.url_entry.get()
            
            # 使用JavaScript创建并点击链接来打开新标签页
            js_script = """
                const a = document.createElement('a');
                a.href = arguments[0];
                a.target = '_blank';
                a.rel = 'noopener noreferrer';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            """
            self.driver.execute_script(js_script, target_url)
            
            # 等待新标签页打开
            time.sleep(1)
            
            # 切换到新打开的标签页
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            # 等待页面加载完成
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script('return document.readyState') == 'complete'
            )
            
            self.update_status(f"已在新标签页打开: {target_url}")   
                
            # 开始监控价格
            while not self.stop_event.is_set():  # 改用事件判断
                try:
                    self.check_balance()
                    self.check_prices()
                    time.sleep(2)
                except Exception as e:
                    if not self.stop_event.is_set():  # 仅在未停止时记录错误
                        self.logger.error(f"监控失败: {str(e)}")
                    time.sleep(self.retry_interval)
        except Exception as e:
            if not self.stop_event.is_set():
                self.logger.error(f"加载页面失败: {str(e)}")
            self.stop_monitoring()
    
    def restart_browser(self):
        # 自动修复: 尝试重新连接浏览器
        try:
            self.logger.info("正在尝试自动修复URL监控...")
            
            # 获取当前脚本的完整路径
            script_path = os.path.abspath('start_chrome.sh')
            # 使用osascript打开新终端并执行脚本
            os.system(f'''osascript -e 'tell application "Terminal" to do script "cd {os.getcwd()} && bash {script_path}"' ''')
            self.logger.info("已在新终端中启动Chrome浏览器")
            # 等待Chrome启动
            time.sleep(5)
            self.driver.get(self.target_url)
            time.sleep(1)
            # 点击登录按钮
            try:
                login_button = self.driver.find_element(By.XPATH, XPathConfig.LOGIN_BUTTON)
                login_button.click()
            except Exception as e:
                login_button = self._find_element_with_retry(
                    XPathConfig.LOGIN_BUTTON,
                    timeout=3,
                    silent=True
                )
                login_button.click()
            time.sleep(1)
            
            # 使用 XPath 定位并点击 MetaMask 按钮
            metamask_button = self._find_element_with_retry(XPathConfig.METAMASK_BUTTON)
            metamask_button.click()
            time.sleep(2)

            # 获取屏幕尺寸
            monitor = get_monitors()[0]  # 获取主屏幕信息
            screen_width, screen_height = monitor.width, monitor.height
            time.sleep(1)
            # 截取屏幕右上角区域用于OCR识别
            # 区域参数格式为(left, top, width, height)
            right_top_region = (screen_width - 400, 0, 400, 600)  # 右上角500x700像素区域
            screen = pyautogui.screenshot(region=right_top_region)
            time.sleep(2)
            # 使用OCR识别文本
            text_chi_sim = pytesseract.image_to_string(screen, lang='chi_sim')
            time.sleep(3)

            # 检查是否包含"欢迎回来!"
            if "欢迎" in text_chi_sim or "回来" in text_chi_sim :
                self.logger.info("检测到MetaMask登录窗口,显示'欢迎回来!'")
                # 输入密码
                pyautogui.write("noneboy780308")
                time.sleep(1)
                # 按下Enter键
                pyautogui.press('enter')
                time.sleep(3)
                
                """屏幕分辨率必须设置为 1920*1080"""
                # 计算 MetaMask 弹窗的 "连接" 按钮位置
                connect_button_x = screen_width - 95  # 按钮位于屏幕右侧，稍微向左偏移范围 92-120
                connect_button_y = 610  # 观察图片后估算按钮的Y坐标,范围 590-620
                time.sleep(2)
                # 点击 "连接" 按钮
                pyautogui.click(connect_button_x, connect_button_y) 
                
                # 计算 "确认" 按钮位置
                confirm_button_x = screen_width - 95  # 同样靠右对齐
                confirm_button_y = 610  # "确认" 按钮通常在下方
                time.sleep(2)
                # 点击 "确认" 按钮
                pyautogui.click(confirm_button_x, confirm_button_y) 

                self.logger.info("MetaMask登录成功")
                time.sleep(1)

            self.start_url_monitoring()
            self.start_login_monitoring()
            self.refresh_page()
            self.start_auto_find_coin()
        except Exception as e:
            self.logger.error(f"自动修复失败: {e}")
        
    def check_prices(self):
        """检查价格变化"""
        try:
            # 检查浏览器连接
            if not self._is_browser_alive():
                self._reconnect_browser()

            if not self.driver:
                self.restart_browser()
                
            # 添加URL检查
            target_url = self.url_entry.get()
            current_url = self.driver.current_url

            if target_url != current_url:
                self.logger.warning(f"检测到URL变化,正在返回监控地址: {target_url}")
                self.driver.get(target_url)
                # 等待页面完全加载
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script('return document.readyState') == 'complete'
                )
                self.update_status("已恢复到监控地址")
            
            try:
                # 使用JavaScript直接获取价格
                prices = self.driver.execute_script("""
                    function getPrices() {
                        const prices = {yes: null, no: null};
                        const elements = document.getElementsByTagName('span');
                        
                        for (let el of elements) {
                            const text = el.textContent.trim();
                            if (text.includes('Yes') && text.includes('¢')) {
                                const match = text.match(/(\\d+\\.?\\d*)¢/);
                                if (match) prices.yes = parseFloat(match[1]);
                            }
                            if (text.includes('No') && text.includes('¢')) {
                                const match = text.match(/(\\d+\\.?\\d*)¢/);
                                if (match) prices.no = parseFloat(match[1]);
                            }
                        }
                        return prices;
                    }
                    return getPrices();
                """)
                
                if prices['yes'] is not None and prices['no'] is not None:
                    yes_price = float(prices['yes']) / 100
                    no_price = float(prices['no']) / 100
                    
                    # 更新价格显示
                    self.yes_price_label.config(
                        text=f"Yes: {prices['yes']}¢ (${yes_price:.2f})",
                        foreground='red'
                    )
                    self.no_price_label.config(
                        text=f"No: {prices['no']}¢ (${no_price:.2f})",
                        foreground='red'
                    )
                    
                    # 更新最后更新时间
                    current_time = datetime.now().strftime('%H:%M:%S')
                    self.last_update_label.config(text=f"最后更新: {current_time}")
                    
                    # 执行所有交易检查函数
                    self.First_trade()
                    self.Second_trade()
                    self.Third_trade()
                    self.Forth_trade()
                    self.Sell_yes()
                    self.Sell_no() 
                else:
                    self.update_status("无法获取价格数据")  
            except Exception as e:
                self.logger.error(f"Fail: {str(e)}")
                self.update_status(f"Fail: {str(e)}")
                self.yes_price_label.config(text="Yes: Fail", foreground='red')
                self.no_price_label.config(text="No: Fail", foreground='red')
                self.root.after(3000, self.check_prices)
        except Exception as e:
            self.logger.error(f"检查价格失败: {str(e)}")
           
            time.sleep(2)

    def check_balance(self):
        """获取Portfolio和Cash值"""
        try:
            if not self.driver:
                self.restart_browser()

            # 等待页面完全加载
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script('return document.readyState') == 'complete'
            )
            
            try:
                # 取Portfolio值
                try:
                    portfolio_element = self.driver.find_element(By.XPATH, XPathConfig.PORTFOLIO_VALUE)
                    self.portfolio_value = portfolio_element.text
                except Exception as e:
                    portfolio_element = self._find_element_with_retry(XPathConfig.PORTFOLIO_VALUE)
                    self.portfolio_value = portfolio_element.text
            
                # 获取Cash值
                try:
                    cash_element = self.driver.find_element(By.XPATH, XPathConfig.CASH_VALUE)
                    self.cash_value = cash_element.text
                except Exception as e:
                    cash_element = self._find_element_with_retry(XPathConfig.CASH_VALUE)
                    self.cash_value = cash_element.text
                
                # 更新Portfolio和Cash显示
                self.portfolio_label.config(text=f"Portfolio: {self.portfolio_value}")
                self.cash_label.config(text=f"Cash: {self.cash_value}")

                # 新增触发条件：首次获取到Cash值时安排设置金额
                if not hasattr(self, 'cash_initialized'):
                    self.cash_initialized = True
                    self.root.after(1000, self.schedule_update_amount)  # 延迟1秒确保数据稳定

                # 新最后更新间
                current_time = datetime.now().strftime('%H:%M:%S')
                self.balance_update_label.config(text=f"最后更新: {current_time}")  
                
            except Exception as e:
                self.logger.error(f"获取资金信息失败: {str(e)}")
                self.portfolio_label.config(text="Portfolio: Fail")
                self.cash_label.config(text="Cash: Fail")
                self.root.after(3000, self.check_balance)
        except Exception as e:
            self.logger.error(f"检查资金失败: {str(e)}")
            
            time.sleep(2)    
    """以上代码执行了监控价格和获取 CASH 的值。从这里开始程序返回到第 740 行"""  

    """以下代码是设置 YES/NO 金额的函数,直到第 1127 行"""
    def schedule_update_amount(self, retry_count=0):
        """设置金额,带重试机制"""
        try:
            if retry_count < 15:  # 最多重试15次
                # 1秒后执行
                self.root.after(1000, lambda: self.try_update_amount(retry_count))
            else:
                self.logger.warning("更新金额操作达到最大重试次数")
        except Exception as e:
            self.logger.error(f"安排更新金额操作失败: {str(e)}")

    def try_update_amount(self, current_retry=0):
        """尝试设置金额"""
        try:
            self.set_amount_button.invoke()
            self.root.after(1000, lambda: self.check_amount_and_set_price(current_retry))
        except Exception as e:
            self.logger.error(f"更新金额操作失败 (尝试 {current_retry + 1}/15): {str(e)}")
            # 如果失败，安排下一次重试
            self.schedule_update_amount(current_retry + 1)

    def check_amount_and_set_price(self, current_retry):
        """检查金额是否设置成功,成功后设置价格"""
        try:
            # 检查yes金额是否为非0值
            yes1_amount = self.yes1_amount_entry.get().strip()

            if yes1_amount and yes1_amount != '0.0':
                # 延迟1秒设置价格
                self.root.after(2000, lambda: self.set_yes_no_default_target_price())
                # 延迟2秒启动刷新页面
                self.root.after(3000, self.driver.refresh())
            else:
                if current_retry < 15:  # 最多重试15次
                    self.logger.info("❌ 金额未成功设置,2秒后重试")
                    self.root.after(2000, lambda: self.check_amount_and_set_price(current_retry))
                else:
                    self.logger.warning("金额设置超时")
        except Exception as e:
            self.logger.error(f"检查金额设置状态失败: {str(e)}")

    def set_yes_no_default_target_price(self):
        """设置默认目标价格"""
        self.yes1_price_entry.delete(0, tk.END)
        self.yes1_price_entry.insert(0, self.default_target_price)
        self.no1_price_entry.delete(0, tk.END)
        self.no1_price_entry.insert(0, self.default_target_price)
        self.logger.info(f"✅ 设置买入价格{self.default_target_price}成功")

    def set_yes_no_cash(self):
        """设置 Yes/No 各级金额"""
        if not hasattr(self, 'cash_initialized'):
            self.logger.warning("Cash数据尚未就绪,延迟设置金额")
            self.root.after(1000, self.set_yes_no_cash)
            return
        try:
            #设置重试参数
            max_retry = 15
            retry_count = 0
            cash_value = None

            while retry_count < max_retry:
                try:
                    # 获取 Cash 值
                    cash_text = self.cash_label.cget("text") 
                    # 使用正则表达式提取数字
                    cash_match = re.search(r'\$?([\d,]+\.?\d*)', cash_text)
                    if not cash_match:
                        raise ValueError("无法从Cash值中提取数字")
                    # 移除逗号并转换为浮点数
                    cash_value = float(cash_match.group(1).replace(',', ''))
                    self.logger.info(f"✅ 提取到Cash值: {cash_value}")
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retry:
                        time.sleep(2)
                    else:
                        raise ValueError("获取Cash值失败")
            if cash_value is None:
                raise ValueError("获取Cash值失败")
            
            # 获取金额设置中的百分比值
            initial_percent = float(self.initial_amount_entry.get()) / 100  # 初始金额百分比
            first_rebound_percent = float(self.first_rebound_entry.get()) / 100  # 反水一次百分比
            n_rebound_percent = float(self.n_rebound_entry.get()) / 100  # 反水N次百分比

            # 设置 Yes1 和 No1金额
            base_amount = cash_value * initial_percent
            self.yes1_entry = self.yes_frame.grid_slaves(row=1, column=1)[0]
            self.yes1_amount_entry.delete(0, tk.END)
            self.yes1_amount_entry.insert(0, f"{base_amount:.2f}")
            self.no1_entry = self.no_frame.grid_slaves(row=1, column=1)[0]
            self.no1_amount_entry.delete(0, tk.END)
            self.no1_amount_entry.insert(0, f"{base_amount:.2f}")
            
            # 计算并设置 Yes2/No2金额
            self.yes2_amount = base_amount * first_rebound_percent
            self.yes2_entry = self.yes_frame.grid_slaves(row=3, column=1)[0]
            self.yes2_entry.delete(0, tk.END)
            self.yes2_entry.insert(0, f"{self.yes2_amount:.2f}")
            self.no2_entry = self.no_frame.grid_slaves(row=3, column=1)[0]
            self.no2_entry.delete(0, tk.END)
            self.no2_entry.insert(0, f"{self.yes2_amount:.2f}")
            
            # 计算并设置 YES3/NO3 金额
            self.yes3_amount = self.yes2_amount * n_rebound_percent
            self.yes3_entry = self.yes_frame.grid_slaves(row=5, column=1)[0]
            self.yes3_entry.delete(0, tk.END)
            self.yes3_entry.insert(0, f"{self.yes3_amount:.2f}")
            self.no3_entry = self.no_frame.grid_slaves(row=5, column=1)[0]
            self.no3_entry.delete(0, tk.END)
            self.no3_entry.insert(0, f"{self.yes3_amount:.2f}")

            # 计算并设置 Yes4/No4金额
            self.yes4_amount = self.yes3_amount * n_rebound_percent
            self.yes4_entry = self.yes_frame.grid_slaves(row=7, column=1)[0]
            self.yes4_entry.delete(0, tk.END)
            self.yes4_entry.insert(0, f"{self.yes4_amount:.2f}")
            self.no4_entry = self.no_frame.grid_slaves(row=7, column=1)[0]
            self.no4_entry.delete(0, tk.END)
            self.no4_entry.insert(0, f"{self.yes4_amount:.2f}")
        
            self.logger.info("✅ YES/NO 金额设置完成")
            self.update_status("金额设置成功")
            
        except Exception as e:
            self.logger.error(f"设置金额失败: {str(e)}")
            self.update_status("金额设置失败,请检查Cash值是否正确")
            # 如果失败，安排重试
            self.schedule_retry_update()

    def schedule_retry_update(self):
        """安排重试更新金额"""
        if hasattr(self, 'retry_timer'):
            self.root.after_cancel(self.retry_timer)
        self.retry_timer = self.root.after(3000, self.set_yes_no_cash)  # 3秒后重试
    """以上代码执行了设置 YES/NO 金额的函数,从 1000 行到 1127 行,程序执行返回到 745 行"""

    """以下代码是启动 URL 监控和登录状态监控的函数,直到第 1426 行"""
    def start_url_monitoring(self):
        """启动URL监控"""
        with self.url_monitoring_lock:
            if getattr(self, 'is_url_monitoring', False):
                self.logger.debug("URL监控已在运行中")
                return
            if not self.driver:
                self.restart_browser()

            self.url_monitoring_running = True
            self.logger.info("✅ 启动URL监控")

            def check_url():
                if self.running and self.driver:
                    try:
                        current_page_url = self.driver.current_url
                        target_url = self.target_url
                        if current_page_url != target_url:
                            self.logger.warning("检测到URL变化,正在恢复...")
                            self.driver.get(target_url)
                            self.logger.info("✅ 已恢复到正确的监控网址")
                    except Exception as e:
                        self.logger.error(f"URL监控出错: {str(e)}")
                        # 重新导航到目标URL
                        if self.driver and self._is_browser_alive():
                            self.driver.get(self.target_url)
                            self.logger.info("✅ URL监控已自动修复")
                    # 继续监控
                    if self.running:
                        self.url_check_timer = self.root.after(3000, check_url)  # 每3秒检查一次
            
            # 开始第一次检查
            self.url_check_timer = self.root.after(1000, check_url)
    
    def _is_browser_alive(self):
        """检查浏览器是否仍然活跃"""
        try:
            # 尝试执行一个简单的JavaScript命令来检查浏览器是否响应
            self.driver.execute_script("return navigator.userAgent")
            return True
        except Exception:
            return False
            
    def _reconnect_browser(self):
        """尝试重新连接浏览器"""
        try:
            # 关闭现有连接（如果有）
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None
                
            # 重新建立连接
            chrome_options = Options()
            chrome_options.debugger_address = "127.0.0.1:9222"
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.logger.info("✅ 已重新连接到浏览器")
            return True
        except Exception as e:
            self.logger.error(f"重新连接浏览器失败: {str(e)}")
            return False

    def stop_url_monitoring(self):
        """停止URL监控"""
        with self.url_monitoring_lock:
            # 检查是否有正在运行的URL监控
            if not hasattr(self, 'url_monitoring_running') or not self.url_monitoring_running:
                self.logger.debug("URL监控未在运行中,无需停止")
                return
            
            # 取消定时器
            if hasattr(self, 'url_check_timer') and self.url_check_timer:
                try:
                    self.root.after_cancel(self.url_check_timer)
                    self.url_check_timer = None
                    
                except Exception as e:
                    self.logger.error(f"取消URL监控定时器时出错: {str(e)}")
            
            # 重置监控状态
            self.url_monitoring_running = False
            
            self.logger.info("❌ URL监控已停止")

    def find_login_button(self):
        """查找登录按钮"""
        # 使用静默模式查找元素，并添加空值检查
        try:
            login_button = self.driver.find_element(By.XPATH, XPathConfig.LOGIN_BUTTON)
        except Exception as e:
            login_button = self._find_element_with_retry(
                XPathConfig.LOGIN_BUTTON,
                timeout=3,
                silent=True
            )
        
        # 添加空值检查和安全访问
        if login_button is not None and "Log In" in login_button.text:
            self.logger.warning("检查到未登录,自动登录...")
            return True
        else:
            # 正常状态无需记录日志
            return False

    def start_login_monitoring(self):
        """启动登录状态监控"""
        self.logger.info("✅ 启动登录状态监控")
        if not self.driver:
            self.restart_browser()
            
        def check_login_status():
            if self.running and self.driver:
                try:
                    # 使用线程执行登录检查，避免阻塞主线程
                    threading.Thread(
                        target=self._check_login_status_thread,
                        daemon=True
                    ).start()
                except Exception as e:
                    self.logger.error(f"登录状态检查出错: {str(e)}")
                
                # 继续监控
                if self.running:
                    self.login_check_timer = self.root.after(10000, check_login_status)  # 每10秒检查一次
        
        # 开始第一次检查
        self.login_check_timer = self.root.after(10000, check_login_status)

    def _check_login_status_thread(self):
        """在单独线程中执行登录检查"""
        try:
            try:
                time.sleep(3)
                if self.find_login_button():
                    self.logger.warning("检测到❌未登录状态，执行登录")
                    # 在主线程中执行登录操作
                    self.root.after(0, self.check_and_handle_login)
                
            except NoSuchElementException:
                # 找不到登录按钮,说明已经登录
                pass   
        except Exception as e:
            self.logger.error(f"登录状态检查线程出错: {str(e)}")

    def check_and_handle_login(self):
        """执行登录操作"""
        try:
            self.logger.info("开始执行登录操作...")
            
            if not self.driver:
                self.restart_browser()
                
            self.start_login_monitoring_running = True
            self.login_running = True
            self.stop_auto_find_coin()
            self.stop_url_monitoring()
            self.stop_refresh_page()
            time.sleep(5)
            
            # 点击登录按钮
            try:
                login_button = self.driver.find_element(By.XPATH, XPathConfig.LOGIN_BUTTON)
                login_button.click()
            except Exception as e:
                login_button = self._find_element_with_retry(
                    XPathConfig.LOGIN_BUTTON,
                    timeout=3,
                    silent=True
                )
                login_button.click()
            time.sleep(1)
            
            # 使用 XPath 定位并点击 MetaMask 按钮
            metamask_button = self._find_element_with_retry(XPathConfig.METAMASK_BUTTON)
            metamask_button.click()
            time.sleep(5)

            # 获取屏幕尺寸
            monitor = get_monitors()[0]  # 获取主屏幕信息
            screen_width, screen_height = monitor.width, monitor.height
            time.sleep(1)

            # 截取屏幕右上角区域用于OCR识别
            # 区域参数格式为(left, top, width, height)
            right_top_region = (screen_width - 400, 0, 400, 600)  # 右上角500x700像素区域
            screen = pyautogui.screenshot(region=right_top_region)
            time.sleep(2)
            # 使用OCR识别文本
            text_chi_sim = pytesseract.image_to_string(screen, lang='chi_sim')
            time.sleep(3)

            # 检查是否包含"欢迎回来!"
            if "欢迎回来" in text_chi_sim:
                self.logger.info("检测到MetaMask登录窗口,显示'欢迎回来!'")
                # 输入密码
                pyautogui.write("noneboy780308")
                time.sleep(1)
                # 按下Enter键
                pyautogui.press('enter')
                time.sleep(3)
                """屏幕分辨率必须设置为 1920*1080"""
                # 计算 MetaMask 弹窗的 "连接" 按钮位置
                connect_button_x = screen_width - 95  # 按钮位于屏幕右侧，稍微向左偏移范围 92-120
                connect_button_y = 610  # 观察图片后估算按钮的Y坐标,范围 590-620
                time.sleep(2)
                # 点击 "连接" 按钮
                pyautogui.click(connect_button_x, connect_button_y) 
                
                # 计算 "确认" 按钮位置
                confirm_button_x = screen_width - 95  # 同样靠右对齐
                confirm_button_y = 610  # "确认" 按钮通常在下方
                time.sleep(2)
                # 点击 "确认" 按钮
                pyautogui.click(confirm_button_x, confirm_button_y) 

                self.logger.info("MetaMask登录成功")
                time.sleep(1)
                
            else:
                """屏幕分辨率必须设置为 1920*1080"""
                # 计算 MetaMask 弹窗的 "连接" 按钮位置
                connect_button_x = screen_width - 95  # 按钮位于屏幕右侧，稍微向左偏移范围 92-120
                connect_button_y = 610  # 观察图片后估算按钮的Y坐标,范围 590-620
                time.sleep(2)
                # 点击 "连接" 按钮
                pyautogui.click(connect_button_x, connect_button_y) 
                
                # 计算 "确认" 按钮位置
                confirm_button_x = screen_width - 95  # 同样靠右对齐
                confirm_button_y = 610  # "确认" 按钮通常在下方
                time.sleep(2)
                # 点击 "确认" 按钮
                pyautogui.click(confirm_button_x, confirm_button_y)  
                
                time.sleep(5)
                
                if self.is_login_successful() and not self.find_login_button():
                    self.logger.info("✅ 登录完成,执行click_accept_button")
                    self.click_accept_button()

                else:
                    self.logger.warning("❌ 登录失败,重新登录")
                    return
                        
        except Exception as e:
            self.logger.error(f"登录操作失败: {str(e)}")
            return False

    def is_login_successful(self):
        """检查登录是否成功"""
        try:
            # 获取Cash值
            try:
                cash_element = self.driver.find_element(By.XPATH, XPathConfig.CASH_VALUE)
                cash_value = cash_element.text
            except Exception as e:
                cash_element = self._find_element_with_retry(XPathConfig.CASH_VALUE)
                cash_value = cash_element.text
            
            if cash_value is not None:
                self.logger.info(f"✅ 检测到CASH值: {cash_value}")
                return True
            else:
                return False
        except NoSuchElementException:
            return False

    def click_accept_button(self):
        """重新登录后,需要在amount输入框输入1并确认"""
        self.logger.info("开始执行click_accept_button")
        self.login_running = True
        try:
            # 等待输入框可交互
            try:
                amount_input = self.driver.find_element(By.XPATH, XPathConfig.AMOUNT_INPUT)
            except Exception as e:
                amount_input = self._find_element_with_retry(
                    XPathConfig.AMOUNT_INPUT,
                    timeout=3,
                    silent=True
                )
            
            # 清除现有输入并输入新值
            amount_input.clear()
            amount_input.send_keys("1")
            time.sleep(1)
            
            # 点击确认按钮
            self.buy_confirm_button.invoke()
            time.sleep(1)
            
            # 获取屏幕尺寸
            monitor = get_monitors()[0]  # 获取主屏幕信息
            screen_width, screen_height = monitor.width, monitor.height
            time.sleep(1)

            # 截取屏幕右上角区域用于OCR识别
            # 区域参数格式为(left, top, width, height)
            # 截图区域从上往下(0,870),从右往左(0,870),
            right_top_region = (screen_width - 870, 0, 870, 870)  
            screen = pyautogui.screenshot(region=right_top_region)
            
            time.sleep(2)
            # 使用OCR识别文本
            text_chi_sim = pytesseract.image_to_string(screen, lang='chi_sim')
            time.sleep(3)

            if "Accept" in text_chi_sim:
                self.logger.info("检测到MetaMask弹窗,显示'Accept'")
                # 点击 "Accept" 按钮
                pyautogui.press('enter')
                self.logger.info("✅ click_accept_button执行完成")
            else:
                # 计算 "取消" 按钮位置
                cancel_button_x = screen_width - 170  # 同样靠右对齐
                cancel_button_y = 610  # "确认" 按钮通常在下方
                time.sleep(2)
                # 点击 "取消" 按钮
                pyautogui.click(cancel_button_x, cancel_button_y)  
            
            # 启动URL监控    
            self.start_url_monitoring()
            # 启动页面刷新
            self.refresh_page()
            
        except Exception as e:
            self.logger.error(f"click_accept_button执行失败: {str(e)}")
            
        finally:
            self.login_running = False

    # 添加刷新方法
    def refresh_page(self):
        """定时刷新页面"""
        with self.refresh_page_lock:
            self.refresh_page_running = True
            try:
                if self.running and self.driver and not self.trading:
                    self.driver.refresh()
                    self.logger.info(f"✅ 定时刷新成功")      
                else:
                    self.logger.info("刷新失败")
                    self.logger.info(f"trading={self.trading}")
            except Exception as e:
                self.logger.error(f"页面刷新失败")
                # 无论是否执行刷新都安排下一次（确保循环持续）
                if hasattr(self, 'refresh_page_timer') and self.refresh_page_timer:
                    try:
                        self.root.after_cancel(self.refresh_page_timer)
                    except Exception as e:
                        self.logger.error(f"取消旧定时器失败")
            finally:
                self.refresh_page_timer = self.root.after(self.refresh_interval, self.refresh_page)
            
    def stop_refresh_page(self):
        """停止页面刷新"""
        with self.refresh_page_lock:
            
            if hasattr(self, 'refresh_page_timer') and self.refresh_page_timer:
                try:
                    self.root.after_cancel(self.refresh_page_timer)
                    self.refresh_page_timer = None
                    self.logger.info("❌ 刷新定时器已停止")
                except Exception as e:
                    self.logger.error("取消页面刷新定时器时出错")
            # 重置监控状态
            self.refresh_page_running = False
            self.logger.info("❌ 刷新状态已停止")
    """以上代码执行了登录操作的函数,直到第 1315 行,程序执行返回到 748 行"""
   
    """以下代码是监控买卖条件及执行交易的函数,程序开始进入交易阶段,从 1468 行直到第 2224200 行"""  
    def is_accept(self):
        # 获取屏幕尺寸
        monitor = get_monitors()[0]  # 获取主屏幕信息
        screen_width, screen_height = monitor.width, monitor.height
        time.sleep(1)

        # 截取屏幕右上角区域用于OCR识别
        # 区域参数格式为(left, top, width, height)
        # 截图区域从上往下(0,870),从右往左(0,870),
        right_top_region = (screen_width - 870, 0, 870, 870)  
        screen = pyautogui.screenshot(region=right_top_region)
        
        time.sleep(2)
        # 使用OCR识别文本
        text_chi_sim = pytesseract.image_to_string(screen, lang='chi_sim')
        time.sleep(3)

        if "Accept" in text_chi_sim:
            self.logger.info("检测到MetaMask弹窗,显示'Accept'")
            # 点击 "Accept" 按钮
            pyautogui.press('enter')
            self.logger.info("✅ 点击 ACCEPT 执行完成")
            
            return True
        else:
            return False

    def First_trade(self):
        try:
            # 获取当前Yes和No价格
            prices = self.driver.execute_script("""
                function getPrices() {
                    const prices = {yes: null, no: null};
                    const elements = document.getElementsByTagName('span');
                    
                    for (let el of elements) {
                        const text = el.textContent.trim();
                        if (text.includes('Yes') && text.includes('¢')) {
                            const match = text.match(/(\\d+\\.?\\d*)¢/);
                            if (match) prices.yes = parseFloat(match[1]);
                        }
                        if (text.includes('No') && text.includes('¢')) {
                            const match = text.match(/(\\d+\\.?\\d*)¢/);
                            if (match) prices.no = parseFloat(match[1]);
                        }
                    }
                    return prices;
                }
                return getPrices();
            """)
                
            if prices['yes'] is not None and prices['no'] is not None:
                yes_price = float(prices['yes']) / 100
                no_price = float(prices['no']) / 100
                
                # 获取Yes1和No1的目标价格
                yes1_target = float(self.yes1_price_entry.get())
                no1_target = float(self.no1_price_entry.get())
                self.trading = True  # 开始交易
                # 检查Yes1价格匹配
                if 0 <= (yes_price - yes1_target ) <= 0.03 and yes1_target > 0:
                    while True:
                        self.logger.info("Yes 1价格匹配,执行自动交易")
                        # 执行现有的交易操作
                        self.amount_yes1_button.event_generate('<Button-1>')
                        time.sleep(0.5)
                        self.buy_confirm_button.invoke()
                        self.is_accept()
                        self.buy_confirm_button.invoke()
                        time.sleep(0.5)
                        self._handle_metamask_popup()
                        # 执行等待和刷新
                        self.sleep_refresh("First_trade")
                        if self.Verify_buy_yes():
                            # 增加交易次数
                            self.trade_count += 1
                            # 发送交易邮件
                            self.send_trade_email(
                                trade_type="Buy Yes1",
                                price=yes_price,
                                amount=float(self.yes1_amount_entry.get()),
                                trade_count=self.trade_count
                            )
                            # 重置Yes1和No1价格为0.00
                            self.yes1_price_entry.delete(0, tk.END)
                            self.yes1_price_entry.insert(0, "0.00")
                            self.no1_price_entry.delete(0, tk.END)
                            self.no1_price_entry.insert(0, "0.00")
                                
                            # 设置No2价格为默认值
                            self.no2_price_entry = self.no_frame.grid_slaves(row=2, column=1)[0]
                            self.no2_price_entry.delete(0, tk.END)
                            self.no2_price_entry.insert(0, str(self.default_target_price))
                            self.no2_price_entry.configure(foreground='red')  # 添加红色设置

                            # 设置 Yes5和No5价格为0.85
                            self.yes5_price_entry = self.yes_frame.grid_slaves(row=8, column=1)[0]
                            self.yes5_price_entry.delete(0, tk.END)
                            self.yes5_price_entry.insert(0, "0.85")
                            self.yes5_price_entry.configure(foreground='red')  # 添加红色设置
                            self.no5_price_entry = self.no_frame.grid_slaves(row=8, column=1)[0]
                            self.no5_price_entry.delete(0, tk.END)
                            self.no5_price_entry.insert(0, "0.85")
                            self.no5_price_entry.configure(foreground='red')  # 添加红色设置
                            self.logger.info("First_trade执行成功")
                            break
                        else:
                            self.logger.warning("交易失败,等待2秒后重试")
                            time.sleep(2)  # 添加延时避免过于频繁的重试

                # 检查No1价格匹配
                elif 0 <= (no_price - no1_target ) <= 0.03 and no1_target > 0:
                    while True:
                        self.logger.info("No 1价格匹配,执行自动交易") 
                        # 执行现有的交易操作
                        self.buy_no_button.invoke()
                        time.sleep(0.5)
                        self.amount_no1_button.event_generate('<Button-1>')
                        time.sleep(0.5)
                        self.buy_confirm_button.invoke()
                        time.sleep(1)
                        self.is_accept()
                        self.buy_confirm_button.invoke()
                        
                        self._handle_metamask_popup()
                        # 执行等待和刷新
                        self.sleep_refresh("First_trade")

                        if self.Verify_buy_no():
                            # 增加交易次数
                            self.trade_count += 1
                            # 发送交易邮件
                            self.send_trade_email(
                                trade_type="Buy No1",
                                price=no_price,
                                amount=float(self.no1_amount_entry.get()),
                                trade_count=self.trade_count
                            )
                            # 重置Yes1和No1价格为0.00
                            self.yes1_price_entry.delete(0, tk.END)
                            self.yes1_price_entry.insert(0, "0.00")
                            self.no1_price_entry.delete(0, tk.END)
                            self.no1_price_entry.insert(0, "0.00")
                            
                            # 设置Yes2价格为默认值
                            self.yes2_price_entry = self.yes_frame.grid_slaves(row=2, column=1)[0]
                            self.yes2_price_entry.delete(0, tk.END)
                            self.yes2_price_entry.insert(0, str(self.default_target_price))
                            self.yes2_price_entry.configure(foreground='red')  # 添加红色设置

                            # 设置 Yes5和No5价格为0.85
                            self.yes5_price_entry = self.yes_frame.grid_slaves(row=8, column=1)[0]
                            self.yes5_price_entry.delete(0, tk.END)
                            self.yes5_price_entry.insert(0, "0.85")
                            self.yes5_price_entry.configure(foreground='red')  # 添加红色设置
                            self.no5_price_entry = self.no_frame.grid_slaves(row=8, column=1)[0]
                            self.no5_price_entry.delete(0, tk.END)
                            self.no5_price_entry.insert(0, "0.85")
                            self.no5_price_entry.configure(foreground='red')  # 添加红色设置
                            self.logger.info("First_trade执行成功")
                            break
                        else:
                            self.logger.warning("交易失败,等待2秒后重试")
                            time.sleep(2)  # 添加延时避免过于频繁的重试                           
        except ValueError as e:
            self.logger.error(f"价格转换错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"First_trade执行失败: {str(e)}")
            self.update_status(f"First_trade执行失败: {str(e)}")
        finally:
            self.trading = False
            
    def Second_trade(self):
        """处理Yes2/No2的自动交易"""
        try:
            # 获取当前Yes和No价格
            prices = self.driver.execute_script("""
                function getPrices() {
                    const prices = {yes: null, no: null};
                    const elements = document.getElementsByTagName('span');
                    
                    for (let el of elements) {
                        const text = el.textContent.trim();
                        if (text.includes('Yes') && text.includes('¢')) {
                            const match = text.match(/(\\d+\\.?\\d*)¢/);
                            if (match) prices.yes = parseFloat(match[1]);
                        }
                        if (text.includes('No') && text.includes('¢')) {
                            const match = text.match(/(\\d+\\.?\\d*)¢/);
                            if (match) prices.no = parseFloat(match[1]);
                        }
                    }
                    return prices;
                }
                return getPrices();
            """)

            if prices['yes'] is not None and prices['no'] is not None:
                yes_price = float(prices['yes']) / 100
                no_price = float(prices['no']) / 100
                
                # 获Yes2和No2的价格输入框
                yes2_target = float(self.yes2_price_entry.get())
                no2_target = float(self.no2_price_entry.get())
                self.trading = True  # 开始交易
            
                # 检查Yes2价格匹配
                if 0 <= (yes_price - yes2_target ) <= 0.03 and yes2_target > 0:
                    while True:
                        self.logger.info("Yes 2价格匹配,执行自动交易")
                        # 执行现有的交易操作
                        self.amount_yes2_button.event_generate('<Button-1>')
                        time.sleep(0.5)
                        self.buy_confirm_button.invoke()
                        time.sleep(1)
                        self.is_accept()
                        self.buy_confirm_button.invoke()
                        self._handle_metamask_popup()
                        # 执行等待和刷新
                        self.sleep_refresh("Second_trade")
                        if self.Verify_buy_yes():
                            
                            # 重置Yes2和No2价格为0.00
                            self.yes2_price_entry.delete(0, tk.END)
                            self.yes2_price_entry.insert(0, "0.00")
                            self.no2_price_entry.delete(0, tk.END)
                            self.no2_price_entry.insert(0, "0.00")
                            
                            # 设置No3价格为默认值
                            self.no3_price_entry = self.no_frame.grid_slaves(row=4, column=1)[0]
                            self.no3_price_entry.delete(0, tk.END)
                            self.no3_price_entry.insert(0, str(self.default_target_price))
                            self.no3_price_entry.configure(foreground='red')  # 添加红色设置
                            
                            # 增加交易次数
                            self.trade_count += 1
                            # 发送交易邮件
                            self.send_trade_email(
                                trade_type="Buy Yes 2",
                                price=yes_price,
                                amount=float(self.buy_yes_amount),
                                trade_count=self.trade_count
                            )
                            self.logger.info("Second_trade执行成功")
                            break
                        else:
                            self.logger.warning("交易失败,等待2秒后重试")
                            time.sleep(2)  # 添加延时避免过于频繁的重试
                # 检查No2价格匹配
                elif 0 <= (no_price - no2_target ) <= 0.03 and no2_target > 0:
                    while True:
                        self.logger.info("No 2价格匹配,执行自动交易")
                        
                        # 执行现有的交易操作
                        self.buy_no_button.invoke()
                        time.sleep(0.5)
                        self.amount_no2_button.event_generate('<Button-1>')
                        time.sleep(0.5)
                        self.buy_confirm_button.invoke()
                        time.sleep(1)
                        self.is_accept()
                        self.buy_confirm_button.invoke()
                        self._handle_metamask_popup()
                        # 执行等待和刷新
                        self.sleep_refresh("Second_trade")
                        if self.Verify_buy_no():

                            # 重置Yes2和No2价格为0.00
                            self.yes2_price_entry.delete(0, tk.END)
                            self.yes2_price_entry.insert(0, "0.00")
                            self.no2_price_entry.delete(0, tk.END)
                            self.no2_price_entry.insert(0, "0.00")
                            
                            # 设置Yes3价格为默认值
                            self.yes3_price_entry = self.yes_frame.grid_slaves(row=4, column=1)[0]
                            self.yes3_price_entry.delete(0, tk.END)
                            self.yes3_price_entry.insert(0, str(self.default_target_price))
                            self.yes3_price_entry.configure(foreground='red')  # 添加红色设置
                            
                            # 增加交易次数
                            self.trade_count += 1
                            # 发送交易邮件
                            self.send_trade_email(
                                trade_type="Buy No 2",
                                price=no_price,
                                amount=float(self.buy_no_amount),
                                trade_count=self.trade_count
                            )
                            self.logger.info("Second_trade执行成功")
                            break
                        else:
                            self.logger.warning("交易失败,等待2秒后重试")
                            time.sleep(2)  # 添加延时避免过于频繁的重试
        except ValueError as e:
            self.logger.error(f"价格转换错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"Second_trade执行失败: {str(e)}")
            self.update_status(f"Second_trade执行失败: {str(e)}")
        finally:
            self.trading = False
            
    def Third_trade(self):
        """处理Yes3/No3的自动交易"""
        try:
            # 获取当前Yes和No价格
            prices = self.driver.execute_script("""
                function getPrices() {
                    const prices = {yes: null, no: null};
                    const elements = document.getElementsByTagName('span');
                    
                    for (let el of elements) {
                        const text = el.textContent.trim();
                        if (text.includes('Yes') && text.includes('¢')) {
                            const match = text.match(/(\\d+\\.?\\d*)¢/);
                            if (match) prices.yes = parseFloat(match[1]);
                        }
                        if (text.includes('No') && text.includes('¢')) {
                            const match = text.match(/(\\d+\\.?\\d*)¢/);
                            if (match) prices.no = parseFloat(match[1]);
                        }
                    }
                    return prices;
                }
                return getPrices();
            """)
                
            if prices['yes'] is not None and prices['no'] is not None:
                yes_price = float(prices['yes']) / 100
                no_price = float(prices['no']) / 100
                
                # 获取Yes3和No3的价格输入框
                yes3_target = float(self.yes3_price_entry.get())
                no3_target = float(self.no3_price_entry.get())
                self.trading = True  # 开始交易
            
                # 检查Yes3价格匹配
                if 0 <= (yes_price - yes3_target ) <= 0.03 and yes3_target > 0:
                    while True:
                        self.logger.info("Yes 3价格匹配,执行自动交易")
                        # 执行交易操作
                        self.amount_yes3_button.event_generate('<Button-1>')
                        time.sleep(0.5)
                        self.buy_confirm_button.invoke()
                        time.sleep(1)
                        self.is_accept()
                        self.buy_confirm_button.invoke()
                        self._handle_metamask_popup()
                        # 执行等待和刷新
                        self.sleep_refresh("Third_trade")
                        if self.Verify_buy_yes():

                            # 重置Yes3和No3价格为0.00
                            self.yes3_price_entry.delete(0, tk.END)
                            self.yes3_price_entry.insert(0, "0.00")
                            self.no3_price_entry.delete(0, tk.END)
                            self.no3_price_entry.insert(0, "0.00")
                            
                            # 设置No4价格为默认值
                            self.no4_price_entry = self.no_frame.grid_slaves(row=6, column=1)[0]
                            self.no4_price_entry.delete(0, tk.END)
                            self.no4_price_entry.insert(0, str(self.default_target_price))
                            self.no4_price_entry.configure(foreground='red')  # 添加红色设置

                            # 增加交易次数
                            self.trade_count += 1
                            # 发送交易邮件
                            self.send_trade_email(
                                trade_type="Buy Yes 3",
                                price=yes_price,
                                amount=float(self.buy_yes_amount),
                                trade_count=self.trade_count
                            )   
                            self.logger.info("Third_trade执行成功")
                            break
                        else:
                            self.logger.warning("交易失败,等待2秒后重试")
                            time.sleep(2)  # 添加延时避免过于频繁的重试
                # 检查No3价格匹配
                elif 0 <= (no_price - no3_target ) <= 0.03 and no3_target > 0:
                    while True:
                        self.logger.info("No 3价格匹配,执行自动交易")
                        # 执行交易操作
                        self.buy_no_button.invoke()
                        time.sleep(0.5)
                        self.amount_no3_button.event_generate('<Button-1>')
                        time.sleep(0.5)
                        self.buy_confirm_button.invoke()
                        time.sleep(1)
                        self.is_accept()
                        self.buy_confirm_button.invoke()
                        self._handle_metamask_popup()
                        # 执行等待和刷新
                        self.sleep_refresh("Third_trade")
                        if self.Verify_buy_no():
                            
                            # 重置Yes3和No3价格为0.00
                            self.yes3_price_entry.delete(0, tk.END)
                            self.yes3_price_entry.insert(0, "0.00")
                            self.no3_price_entry.delete(0, tk.END)
                            self.no3_price_entry.insert(0, "0.00")
                            
                            # 设置Yes4价格为默认值
                            self.yes4_price_entry = self.yes_frame.grid_slaves(row=6, column=1)[0]
                            self.yes4_price_entry.delete(0, tk.END)
                            self.yes4_price_entry.insert(0, str(self.default_target_price))
                            self.yes4_price_entry.configure(foreground='red')  # 添加红色设置
                        
                            # 增加交易次数
                            self.trade_count += 1
                            # 发送交易邮件
                            self.send_trade_email(
                                trade_type="Buy No 3",
                                price=no_price,
                                amount=float(self.buy_no_amount),
                                trade_count=self.trade_count
                            )
                            self.logger.info("Third_trade执行成功")
                            break
                        else:
                            self.logger.warning("交易失败,等待2秒后重试")
                            time.sleep(2)  # 添加延时避免过于频繁的重试
        except ValueError as e:
            self.logger.error(f"价格转换错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"Third_trade执行失败: {str(e)}")
            self.update_status(f"Third_trade执行失败: {str(e)}")
        finally:
            self.trading = False
            
    def Forth_trade(self):
        """处理Yes4/No4的自动交易"""
        try:
            # 获取当前Yes和No价格
            prices = self.driver.execute_script("""
                function getPrices() {
                    const prices = {yes: null, no: null};
                    const elements = document.getElementsByTagName('span');
                    
                    for (let el of elements) {
                        const text = el.textContent.trim();
                        if (text.includes('Yes') && text.includes('¢')) {
                            const match = text.match(/(\\d+\\.?\\d*)¢/);
                            if (match) prices.yes = parseFloat(match[1]);
                        }
                        if (text.includes('No') && text.includes('¢')) {
                            const match = text.match(/(\\d+\\.?\\d*)¢/);
                            if (match) prices.no = parseFloat(match[1]);
                        }
                    }
                    return prices;
                }
                return getPrices();
            """)
                
            if prices['yes'] is not None and prices['no'] is not None:
                yes_price = float(prices['yes']) / 100
                no_price = float(prices['no']) / 100
                
                # 获取Yes4和No4的价格输入框
                yes4_target = float(self.yes4_price_entry.get())
                no4_target = float(self.no4_price_entry.get())
                self.trading = True  # 开始交易
            
                # 检查Yes4价格匹配
                if 0 <= (yes_price - yes4_target ) <= 0.03 and yes4_target > 0:
                    while True:
                        self.logger.info("Yes 4价格匹配,执行自动交易")
                        # 执行交易操作
                        self.amount_yes4_button.event_generate('<Button-1>')
                        time.sleep(0.5)
                        self.buy_confirm_button.invoke()
                        time.sleep(1)
                        self.is_accept()
                        self.buy_confirm_button.invoke()
                        self._handle_metamask_popup()
                        # 执行等待和刷新
                        self.sleep_refresh("Forth_trade")
                        if self.Verify_buy_yes():

                            # 重置Yes4和No4价格为0.00
                            self.yes4_price_entry.delete(0, tk.END)
                            self.yes4_price_entry.insert(0, "0.00")
                            self.no4_price_entry.delete(0, tk.END)
                            self.no4_price_entry.insert(0, "0.00")

                            """当买了 4次后预防第 5 次反水，所以价格到了 50 时就平仓，然后再自动开"""
                            # 设置 Yes5和No5价格为0.85
                            self.yes5_price_entry = self.yes_frame.grid_slaves(row=8, column=1)[0]
                            self.yes5_price_entry.delete(0, tk.END)
                            self.yes5_price_entry.insert(0, "0.85")
                            self.yes5_price_entry.configure(foreground='red')  # 添加红色设置
                            self.no5_price_entry = self.no_frame.grid_slaves(row=8, column=1)[0]
                            self.no5_price_entry.delete(0, tk.END)
                            self.no5_price_entry.insert(0, "0.5")
                            self.no5_price_entry.configure(foreground='red')  # 添加红色设置
                            # 增加交易次数
                            self.trade_count += 1
                            # 发送交易邮件
                            self.send_trade_email(
                                trade_type="Buy Yes 4",
                                price=yes_price,
                                amount=float(self.buy_yes_amount),
                                trade_count=self.trade_count
                            )
                            self.logger.info("Forth_trade执行成功")
                            break
                        else:
                            self.logger.warning("交易失败,等待2秒后重试")
                            time.sleep(2)  # 添加延时避免过于频繁的重试
                # 检查No4价格匹配
                elif 0 <= (no_price - no4_target ) <= 0.03 and no4_target > 0:
                    while True:
                        self.logger.info("No 4价格匹配,执行自动交易")
                        # 执行交易操作
                        self.buy_no_button.invoke()
                        time.sleep(0.5)
                        self.amount_no4_button.event_generate('<Button-1>')
                        time.sleep(0.5)
                        self.buy_confirm_button.invoke()
                        time.sleep(1)
                        self.is_accept()
                        self.buy_confirm_button.invoke()
                        self._handle_metamask_popup()
                        # 执行等待和刷新
                        self.sleep_refresh("Forth_trade")
                        if self.Verify_buy_no():
                            # 重置Yes4和No4价格为0.00
                            self.yes4_price_entry.delete(0, tk.END)
                            self.yes4_price_entry.insert(0, "0.00")
                            self.no4_price_entry.delete(0, tk.END)
                            self.no4_price_entry.insert(0, "0.00")

                            """当买了 4次后预防第 5 次反水，所以价格到了 50 时就平仓，然后再自动开"""
                            # 设置 Yes5和No5价格为0.85
                            self.yes5_price_entry = self.yes_frame.grid_slaves(row=8, column=1)[0]
                            self.yes5_price_entry.delete(0, tk.END)
                            self.yes5_price_entry.insert(0, "0.5")
                            self.yes5_price_entry.configure(foreground='red')  # 添加红色设置
                            self.no5_price_entry = self.no_frame.grid_slaves(row=8, column=1)[0]
                            self.no5_price_entry.delete(0, tk.END)
                            self.no5_price_entry.insert(0, "0.85")
                            self.no5_price_entry.configure(foreground='red')  # 添加红色设置
                            # 增加交易次数
                            self.trade_count += 1
                            # 发送交易邮件
                            self.send_trade_email(
                                trade_type="Buy No4",
                                price=no_price,
                                amount=float(self.buy_no_amount),
                                trade_count=self.trade_count
                            )
                            self.logger.info("Forth_trade执行成功")
                            break
                        else:
                            self.logger.warning("交易失败,等待2秒后重试")
                            time.sleep(2)  # 添加延时避免过于频繁的重试
        except ValueError as e:
            self.logger.error(f"价格转换错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"Forth_trade执行失败: {str(e)}")
            self.update_status(f"Forth_trade执行失败: {str(e)}")
        finally:
            self.trading = False
            
    def Sell_yes(self):
        """当YES5价格等于实时Yes价格时自动卖出"""
        try:
            if not self.driver:
                raise Exception("浏览器连接丢失")
                
            # 获取当前Yes价格
            prices = self.driver.execute_script("""
                function getPrices() {
                    const prices = {yes: null, no: null};
                    const elements = document.getElementsByTagName('span');
                    
                    for (let el of elements) {
                        const text = el.textContent.trim();
                        if (text.includes('Yes') && text.includes('¢')) {
                            const match = text.match(/(\\d+\\.?\\d*)¢/);
                            if (match) prices.yes = parseFloat(match[1]);
                        }
                        if (text.includes('No') && text.includes('¢')) {
                            const match = text.match(/(\\d+\\.?\\d*)¢/);
                            if (match) prices.no = parseFloat(match[1]);
                        }
                    }
                    return prices;
                }
                return getPrices();
            """)
                
            if prices['yes'] is not None:
                yes_price = float(prices['yes']) / 100
                
                # 获取Yes5价格
                yes5_target = float(self.yes5_price_entry.get())
                self.trading = True  # 开始交易
                # 检查Yes5价格匹配
                if 0 <= (yes_price - yes5_target) <= 0.05 and yes5_target > 0:
                    self.logger.info("Yes 5价格匹配,执行自动卖出")
                    while True:
                        # 执行卖出YES操作
                        self.only_sell_yes()
                        self.logger.info("卖完 YES 后，再卖 NO")
                        # 卖 NO 之前先检查是否有 NO 标签
                        position_label_no = self.find_position_label_no()
                        if position_label_no == "No":
                            self.only_sell_no()
                        # 重置所有价格
                        for i in range(1,6):  # 1-5
                            yes_entry = getattr(self, f'yes{i}_price_entry', None)
                            no_entry = getattr(self, f'no{i}_price_entry', None)
                            if yes_entry:
                                yes_entry.delete(0, tk.END)
                                yes_entry.insert(0, "0.00")
                            if no_entry:
                                no_entry.delete(0, tk.END)
                                no_entry.insert(0, "0.00")

                        # 在所有操作完成后,优雅退出并重启
                        self.logger.info("准备重启程序...")
                        self.root.after(5000, self.restart_program)  # 5秒后重启
                        break
                    else:
                        self.logger.warning("卖出sell_yes验证失败,重试")
                        time.sleep(2)
        except Exception as e:
            self.logger.error(f"Sell_yes执行失败: {str(e)}")
            self.update_status(f"Sell_yes执行失败: {str(e)}")
        finally:
            self.trading = False
            
    def Sell_no(self):
        """当NO4价格等于实时No价格时自动卖出"""
        try:
            if not self.driver:
                raise Exception("浏览器连接丢失")   
            # 获取当前No价格
            prices = self.driver.execute_script("""
                function getPrices() {
                    const prices = {yes: null, no: null};
                    const elements = document.getElementsByTagName('span');
                    
                    for (let el of elements) {
                        const text = el.textContent.trim();
                        if (text.includes('Yes') && text.includes('¢')) {
                            const match = text.match(/(\\d+\\.?\\d*)¢/);
                            if (match) prices.yes = parseFloat(match[1]);
                        }
                        if (text.includes('No') && text.includes('¢')) {
                            const match = text.match(/(\\d+\\.?\\d*)¢/);
                            if (match) prices.no = parseFloat(match[1]);
                        }
                    }
                    return prices;
                }
                return getPrices();
            """)
                
            if prices['no'] is not None:
                no_price = float(prices['no']) / 100
                
                # 获取No5价格
                no5_target = float(self.no5_price_entry.get())
                self.trading = True  # 开始交易
            
                # 检查No5价格匹配
                if 0 <= (no_price - no5_target) <= 0.05 and no5_target > 0:
                    self.logger.info("No 5价格匹配,执行自动卖出")
                    while True:
                        # 卖完 NO 后，自动再卖 YES                      
                        self.only_sell_no()
                        self.logger.info("卖完 NO 后，再卖 YES")

                        position_label_yes = self.find_position_label_yes()
                        if position_label_yes == "Yes":
                            self.only_sell_yes()

                        # 重置所有价格
                        for i in range(1,6):  # 1-5
                            yes_entry = getattr(self, f'yes{i}_price_entry', None)
                            no_entry = getattr(self, f'no{i}_price_entry', None)
                            if yes_entry:
                                yes_entry.delete(0, tk.END)
                                yes_entry.insert(0, "0.00")
                            if no_entry:
                                no_entry.delete(0, tk.END)
                                no_entry.insert(0, "0.00")

                        # 在所有操作完成后,优雅退出并重启
                        self.logger.info("准备重启程序...")
                        self.root.after(5000, self.restart_program)  # 5秒后重启
                        break
                    else:
                        self.logger.warning("卖出sell_no验证失败,重试")
                        time.sleep(2)
        except Exception as e:
            self.logger.error(f"Sell_no执行失败: {str(e)}")
            self.update_status(f"Sell_no执行失败: {str(e)}")
        finally:
            self.trading = False
            
    def only_sell_yes(self):
        """只卖出YES"""
        # 获取当前价格
        prices = self.driver.execute_script("""
                function getPrices() {
                    const prices = {yes: null, no: null};
                    const elements = document.getElementsByTagName('span');
                    
                    for (let el of elements) {
                        const text = el.textContent.trim();
                        if (text.includes('Yes') && text.includes('¢')) {
                            const match = text.match(/(\\d+\\.?\\d*)¢/);
                            if (match) prices.yes = parseFloat(match[1]);
                        }
                        if (text.includes('No') && text.includes('¢')) {
                            const match = text.match(/(\\d+\\.?\\d*)¢/);
                            if (match) prices.no = parseFloat(match[1]);
                        }
                    }
                    return prices;
                }
                return getPrices();
            """)
        yes_price = float(prices['yes']) / 100 if prices['yes'] else 0

        self.position_sell_yes_button.invoke()
        time.sleep(0.5)
        self.sell_profit_button.invoke()
        self.is_accept()
        self.sell_profit_button.invoke()
        self.sleep_refresh("only_sell_yes")

        if self.Verify_sold_yes():
             # 增加卖出计数
            self.sell_count += 1
                
            # 发送交易邮件 - 卖出YES
            self.send_trade_email(
                trade_type="Sell Yes",
                price=yes_price,
                amount=self.position_yes_cash(),  # 卖出时金额为总持仓
                trade_count=self.sell_count  # 使用卖出计数器
            )
        else:
            self.logger.warning("卖出only_sell_yes验证失败,重试")
            return self.only_sell_yes()        
       
    def only_sell_no(self):
        """只卖出NO"""
        # 获取当前价格
        prices = self.driver.execute_script("""
                function getPrices() {
                    const prices = {yes: null, no: null};
                    const elements = document.getElementsByTagName('span');
                    
                    for (let el of elements) {
                        const text = el.textContent.trim();
                        if (text.includes('Yes') && text.includes('¢')) {
                            const match = text.match(/(\\d+\\.?\\d*)¢/);
                            if (match) prices.yes = parseFloat(match[1]);
                        }
                        if (text.includes('No') && text.includes('¢')) {
                            const match = text.match(/(\\d+\\.?\\d*)¢/);
                            if (match) prices.no = parseFloat(match[1]);
                        }
                    }
                    return prices;
                }
                return getPrices();
            """)
        no_price = float(prices['no']) / 100 if prices['no'] else 0

        self.position_sell_no_button.invoke()
        time.sleep(0.5)
        self.sell_profit_button.invoke()
        self.is_accept()
        self.sell_profit_button.invoke()
        # 执行等待和刷新
        self.sleep_refresh("only_sell_no")
        
        if self.Verify_sold_no():
            # 增加卖出计数
            self.sell_count += 1
                
            # 发送交易邮件 - 卖出NO
            self.send_trade_email(
                trade_type="Sell No",
                price=no_price,
                amount=self.position_no_cash(),  # 卖出时金额为总持仓
                trade_count=self.sell_count  # 使用卖出计数器
            )
        else:
            self.logger.warning("卖出only_sell_no验证失败,重试")
            return self.only_sell_no()
        
    """以上代码是交易主体函数 1-4,从第 1370 行到第 2242行"""

    """以下代码是交易过程中的各种方法函数，涉及到按钮的点击，从第 2244 行到第 2528 行"""
    def click_buy_confirm_button(self):
        try:
            buy_confirm_button = self.driver.find_element(By.XPATH, XPathConfig.BUY_CONFIRM_BUTTON)
            buy_confirm_button.click()
        except Exception as e:
            buy_confirm_button = self._find_element_with_retry(
                XPathConfig.BUY_CONFIRM_BUTTON,
                timeout=3,
                silent=True
            )
            buy_confirm_button.click()
    
    def click_position_sell_no(self):
        """点击 Positions-Sell-No 按钮"""
        try:
            if not self.driver:
                self.update_status("请先连接浏览器")
                return
            # 等待页面加载完成
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script('return document.readyState') == 'complete'
            )
            position_value = None
            position_value = self.find_position_label_yes()
            # 根据position_value的值决定点击哪个按钮
            if position_value == "Yes":
                # 如果第一行是Yes，点击第二的按钮
                try:
                    button = self.driver.find_element(By.XPATH, XPathConfig.POSITION_SELL_NO_BUTTON)
                except Exception as e:
                    button = self._find_element_with_retry(
                        XPathConfig.POSITION_SELL_NO_BUTTON,
                        timeout=3,
                        silent=True
                    )
            else:
                # 如果第一行不存在或不是Yes，使用默认的第一行按钮
                try:
                    button = self.driver.find_element(By.XPATH, XPathConfig.POSITION_SELL_BUTTON)
                except Exception as e:
                    button = self._find_element_with_retry(
                        XPathConfig.POSITION_SELL_BUTTON,
                        timeout=3,
                        silent=True
                    )
            # 执行点击
            self.driver.execute_script("arguments[0].click();", button)
            self.update_status("已点击 Positions-Sell-No 按钮")  
        except Exception as e:
            error_msg = f"点击 Positions-Sell-No 按钮失败: {str(e)}"
            self.logger.error(error_msg)
            self.update_status(error_msg)

    def click_position_sell_yes(self):
        """点击 Positions-Sell-Yes 按钮"""
        try:
            if not self.driver:
                self.update_status("请先连接浏览器")
                return
            # 等待页面加载完成
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script('return document.readyState') == 'complete'
            )
            position_value = None
            position_value = self.find_position_label_no()
            # 根据position_value的值决定点击哪个按钮
            if position_value == "No":
                # 如果第二行是No，点击第一行YES 的 SELL的按钮
                try:
                    button = self.driver.find_element(By.XPATH, XPathConfig.POSITION_SELL_YES_BUTTON)
                except Exception as e:
                    button = self._find_element_with_retry(
                        XPathConfig.POSITION_SELL_YES_BUTTON,
                        timeout=3,
                        silent=True
                    )
            else:
                # 如果第二行不存在或不是No，使用默认的第一行按钮
                try:
                    button = self.driver.find_element(By.XPATH, XPathConfig.POSITION_SELL_BUTTON)
                except Exception as e:
                    button = self._find_element_with_retry(
                        XPathConfig.POSITION_SELL_BUTTON,
                        timeout=3,
                        silent=True
                    )
            # 执行点击
            self.driver.execute_script("arguments[0].click();", button)
            self.update_status("已点击 Positions-Sell-Yes 按钮")  
        except Exception as e:
            error_msg = f"点击 Positions-Sell-Yes 按钮失败: {str(e)}"
            self.logger.error(error_msg)
            self.update_status(error_msg)

    def click_profit_sell(self):
        """点击卖出盈利按钮并处理 MetaMask 弹窗"""
        try:
            if not self.driver:
                self.update_status("请先连接浏览器")
                return
            # 点击Sell-卖出按钮
            try:
                button = self.driver.find_element(By.XPATH, XPathConfig.SELL_PROFIT_BUTTON)
            except Exception as e:
                button = self._find_element_with_retry(
                    XPathConfig.SELL_PROFIT_BUTTON,
                    timeout=3,
                    silent=True
                )
            button.click()
            self.update_status("已点击卖出盈利按钮")
            # 等待MetaMask弹窗出现
            time.sleep(1)
            # 使用统一的MetaMask弹窗处理方法
            self._handle_metamask_popup()
            """ 等待 4 秒，刷新 2 次，预防交易失败 """
            # 等待交易完成
            time.sleep(2)
            self.driver.refresh()
            self.update_status("交易完成并刷新页面")
        except Exception as e:
            error_msg = f"卖出盈利操作失败: {str(e)}"
            self.logger.error(error_msg)
            self.update_status(error_msg)

    def click_buy(self):
        try:
            if not self.driver:
                self.update_status("请先连接浏览器")
                return
            try:
                button = self.driver.find_element(By.XPATH, XPathConfig.BUY_BUTTON)
            except Exception as e:
                button = self._find_element_with_retry(
                    XPathConfig.BUY_BUTTON,
                    timeout=3,
                    silent=True
                )
            button.click()
            self.update_status("已点击 Buy 按钮")
        except Exception as e:
            self.logger.error(f"点击 Buy 按钮失败: {str(e)}")
            self.update_status(f"点击 Buy 按钮失败: {str(e)}")

    def click_buy_yes(self):
        """点击 Buy-Yes 按钮"""
        try:
            if not self.driver:
                self.update_status("请先连接浏器")
                return
            
            try:
                button = self.driver.find_element(By.XPATH, XPathConfig.BUY_YES_BUTTON)
            except Exception as e:
                button = self._find_element_with_retry(
                    XPathConfig.BUY_YES_BUTTON,
                    timeout=3,
                    silent=True
                )
            button.click()
            self.update_status("已点击 Buy-Yes 按钮")
        except Exception as e:
            self.logger.error(f"点击 Buy-Yes 按钮失败: {str(e)}")
            self.update_status(f"点击 Buy-Yes 按钮失败: {str(e)}")

    def click_buy_no(self):
        """点击 Buy-No 按钮"""
        try:
            if not self.driver:
                self.update_status("请先连接浏览器")
                return
            try:
                button = self.driver.find_element(By.XPATH, XPathConfig.BUY_NO_BUTTON)
            except Exception as e:
                button = self._find_element_with_retry(
                    XPathConfig.BUY_NO_BUTTON,
                    timeout=3,
                    silent=True
                )
            button.click()
            self.update_status("已点击 Buy-No 按钮")
        except Exception as e:
            self.logger.error(f"点击 Buy-No 按钮失败: {str(e)}")
            self.update_status(f"点击 Buy-No 按钮失败: {str(e)}")

    def click_sell_yes(self):
        """点击 Sell-Yes 按钮"""
        try:
            if not self.driver:
                self.update_status("请先连接浏览器")
                return
            
            try:
                button = self.driver.find_element(By.XPATH, XPathConfig.SELL_YES_BUTTON)
            except Exception as e:
                button = self._find_element_with_retry(
                    XPathConfig.SELL_YES_BUTTON,
                    timeout=3,
                    silent=True
                )
            button.click()
            self.update_status("已点击 Sell-Yes 按钮")
        except Exception as e:
            self.logger.error(f"点击 Sell-Yes 按钮失败: {str(e)}")
            self.update_status(f"点击 Sell-Yes 按钮失败: {str(e)}")

    def click_sell_no(self):
        """点击 Sell-No 按钮"""
        try:
            if not self.driver:
                self.update_status("请先连接浏览器")
                return
            try:
                button = self.driver.find_element(By.XPATH, XPathConfig.SELL_NO_BUTTON)
            except Exception as e:
                button = self._find_element_with_retry(
                    XPathConfig.SELL_NO_BUTTON,
                    timeout=3,
                    silent=True
                )
            button.click()
            self.update_status("已点击 Sell-No 按钮")
        except Exception as e:
            self.logger.error(f"点击 Sell-No 按钮失败: {str(e)}")
            self.update_status(f"点击 Sell-No 按钮失败: {str(e)}")

    def click_amount(self, event=None):
        """点击 Amount 按钮并输入数量"""
        try:
            if not self.driver:
                self.update_status("请先连接浏览器")
                return         
            
            # 获取触发事件的按钮
            button = event.widget if event else self.amount_button
            button_text = button.cget("text")
            # 找到输入框
            try:
                amount_input = self.driver.find_element(By.XPATH, XPathConfig.AMOUNT_INPUT)
            except Exception as e:
                amount_input = self._find_element_with_retry(
                    XPathConfig.AMOUNT_INPUT,
                    timeout=3,
                    silent=True
                )

            # 清空输入框
            amount_input.clear()
            # 根据按钮文本获取对应的金额
            if button_text == "Amount-Y1":
                amount = self.yes1_amount_entry.get()
            elif button_text == "Amount-Y2":
                yes2_amount_entry = self.yes_frame.grid_slaves(row=3, column=1)[0]
                amount = yes2_amount_entry.get()
            elif button_text == "Amount-Y3":
                yes3_amount_entry = self.yes_frame.grid_slaves(row=5, column=1)[0]
                amount = yes3_amount_entry.get()
            elif button_text == "Amount-Y4":
                yes4_amount_entry = self.yes_frame.grid_slaves(row=7, column=1)[0]
                amount = yes4_amount_entry.get()
            
            # No 按钮
            elif button_text == "Amount-N1":
                no1_amount_entry = self.no_frame.grid_slaves(row=1, column=1)[0]
                amount = no1_amount_entry.get()
            elif button_text == "Amount-N2":
                no2_amount_entry = self.no_frame.grid_slaves(row=3, column=1)[0]
                amount = no2_amount_entry.get()
            elif button_text == "Amount-N3":
                no3_amount_entry = self.no_frame.grid_slaves(row=5, column=1)[0]
                amount = no3_amount_entry.get()
            elif button_text == "Amount-N4":
                no4_amount_entry = self.no_frame.grid_slaves(row=7, column=1)[0]
                amount = no4_amount_entry.get()
            else:
                amount = "0.0"
            # 输入金额
            amount_input.send_keys(str(amount))
            
            self.update_status(f"已在Amount输入框输入: {amount}")    
        except Exception as e:
            self.logger.error(f"Amount操作失败: {str(e)}")
            self.update_status(f"Amount操作失败: {str(e)}")

    """以下代码是交易过程中的功能性函数,买卖及确认买卖成功,从第 2529 行到第 2703 行"""
    def Verify_buy_yes(self):
        """
        验证交易是否成功完成Returns:bool: 交易是否成功
        """
        try:
            # 首先验证浏览器状态
            if not self.driver:
                self.logger.error("浏览器连接已断开")
                return False
            # 等待并检查是否存在 Yes 标签
            try:
                yes_element = self.driver.find_element(By.XPATH, XPathConfig.HISTORY)
            except Exception as e:
                yes_element = self._find_element_with_retry(
                    XPathConfig.HISTORY,
                    timeout=3,
                    silent=True
                )
            text = yes_element.text
            trade_type = re.search(r'\b(Bought)\b', text)  # 匹配单词 Bought
            yes_match = re.search(r'\b(Yes)\b', text)  # 匹配单词 Yes
            amount_match = re.search(r'\$(\d+\.?\d*)', text)  # 匹配 $数字 格式
            
            if trade_type.group(1) == "Bought" and yes_match.group(1) == "Yes":
                self.trade_type = trade_type.group(1)  # 获取 "Bought"
                self.buy_yes_value = yes_match.group(1)  # 获取 "Yes"
                self.buy_yes_amount = float(amount_match.group(1))  # 获取数字部分并转为浮点数
                self.logger.info(f"交易验证成功: {self.trade_type}-{self.buy_yes_value}-${self.buy_yes_amount}")
                return True
            return False       
        except Exception as e:
            self.logger.warning(f"Verify_buy_yes执行失败: {str(e)}")
            return False
        
    def Verify_buy_no(self):
        """
        验证交易是否成功完成
        Returns:
        bool: 交易是否成功
        """
        try:
            # 首先验证浏览器状态
            if not self.driver:
                self.logger.error("浏览器连接已断开")
                return False
            # 等待并检查是否存在 No 标签
            try:
                no_element = self.driver.find_element(By.XPATH, XPathConfig.HISTORY)
            except Exception as e:
                no_element = self._find_element_with_retry(
                    XPathConfig.HISTORY,
                    timeout=3,
                    silent=True
                )
            text = no_element.text

            trade_type = re.search(r'\b(Bought)\b', text)  # 匹配单词 Bought
            no_match = re.search(r'\b(No)\b', text)  # 匹配单词 No
            amount_match = re.search(r'\$(\d+\.?\d*)', text)  # 匹配 $数字 格式

            if trade_type.group(1) == "Bought" and no_match.group(1) == "No":
                self.trade_type = trade_type.group(1)  # 获取 "Bought"
                self.buy_no_value = no_match.group(1)  # 获取 "No"
                self.buy_no_amount = float(amount_match.group(1))  # 获取数字部分并转为浮点数
                self.logger.info(f"交易验证成功: {self.trade_type}-{self.buy_no_value}-${self.buy_no_amount}")
                return True
            return False        
        except Exception as e:
            self.logger.warning(f"Verify_buy_no执行失败: {str(e)}")
            return False
        
    def position_yes_cash(self):
        """获取当前持仓YES的金额"""
        try:
            yes_element = self.driver.find_element(By.XPATH, XPathConfig.HISTORY)
        except Exception as e:
            yes_element = self._find_element_with_retry(
                XPathConfig.HISTORY,
                timeout=3,
                silent=True
            )
        text = yes_element.text
        amount_match = re.search(r'\$(\d+\.?\d*)', text)  # 匹配 $数字 格式
        yes_value = float(amount_match.group(1))
        self.logger.info(f"当前持仓YES的金额: {yes_value}")
        return yes_value
    
    def position_no_cash(self):
        """获取当前持仓NO的金额"""
        try:
            no_element = self.driver.find_element(By.XPATH, XPathConfig.HISTORY)
        except Exception as e:
            no_element = self._find_element_with_retry(
                XPathConfig.HISTORY,
                timeout=3,
                silent=True
            )
        text = no_element.text
        amount_match = re.search(r'\$(\d+\.?\d*)', text)  # 匹配 $数字 格式
        no_value = float(amount_match.group(1))
        self.logger.info(f"当前持仓NO的金额: {no_value}")
        return no_value
    
    def Verify_sold_yes(self):
        """
        验证交易是否成功完成Returns:bool: 交易是否成功
        """
        try:
            # 首先验证浏览器状态
            if not self.driver:
                self.logger.error("浏览器连接已断开")
                return False
            # 等待并检查是否存在 Yes 标签
            try:
                yes_element = self.driver.find_element(By.XPATH, XPathConfig.HISTORY)
            except Exception as e:
                yes_element = self._find_element_with_retry(
                    XPathConfig.HISTORY,
                    timeout=3,
                    silent=True
                )
            text = yes_element.text
            trade_type = re.search(r'\b(Sold)\b', text)  # 匹配单词 Sold
            yes_match = re.search(r'\b(Yes)\b', text)  # 匹配单词 Yes
            amount_match = re.search(r'\$(\d+\.?\d*)', text)  # 匹配 $数字 格式
            
            if trade_type.group(1) == "Sold" and yes_match.group(1) == "Yes":
                self.trade_type = trade_type.group(1)  # 获取 "Sold"
                self.buy_yes_value = yes_match.group(1)  # 获取 "Yes"
                self.buy_yes_amount = float(amount_match.group(1))  # 获取数字部分并转为浮点数
                self.logger.info(f"交易验证成功: {self.trade_type}-{self.buy_yes_value}-${self.buy_yes_amount}")
                return True
            return False       
        except Exception as e:
            self.logger.warning(f"Verify_sold_yes执行失败: {str(e)}")
            return False
        
    def Verify_sold_no(self):
        """
        验证交易是否成功完成
        Returns:
        bool: 交易是否成功
        """
        try:
            # 首先验证浏览器状态
            if not self.driver:
                self.logger.error("浏览器连接已断开")
                return False
            # 等待并检查是否存在 No 标签
            try:
                no_element = self.driver.find_element(By.XPATH, XPathConfig.HISTORY)
            except Exception as e:
                no_element = self._find_element_with_retry(
                    XPathConfig.HISTORY,
                    timeout=3,
                    silent=True
                )
            text = no_element.text

            trade_type = re.search(r'\b(Sold)\b', text)  # 匹配单词 Sold
            no_match = re.search(r'\b(No)\b', text)  # 匹配单词 No
            amount_match = re.search(r'\$(\d+\.?\d*)', text)  # 匹配 $数字 格式

            if trade_type.group(1) == "Sold" and no_match.group(1) == "No":
                self.trade_type = trade_type.group(1)  # 获取 "Sold"
                self.buy_no_value = no_match.group(1)  # 获取 "No"
                self.buy_no_amount = float(amount_match.group(1))  # 获取数字部分并转为浮点数
                self.logger.info(f"交易验证成功: {self.trade_type}-{self.buy_no_value}-${self.buy_no_amount}")
                return True
            return False        
        except Exception as e:
            self.logger.warning(f"Verify_sold_no执行失败: {str(e)}")
            return False
    
    def restart_program(self):
        """重启程序,保持浏览器打开"""
        try:
            self.logger.info("正在重启程序...")
            self.update_status("正在重启程序...")
            # 获取当前脚本的完整路径
            script_path = os.path.abspath('run_trader.sh')
        
            # 使用完整路径和正确的参数顺序
            os.execl('/bin/bash', '/bin/bash', script_path, '--restart')
        
        except Exception as e:
            self.logger.error(f"重启程序失败: {str(e)}")
            self.update_status(f"重启程序失败: {str(e)}")

    def auto_start_monitor(self):
        """自动点击开始监控按钮"""
        try:
            self.logger.info("准备阶段：重置按钮状态")
            # 强制启用开始按钮
            self.start_button['state'] = 'normal'
            self.stop_button['state'] = 'disabled'
            # 清除可能存在的锁定状态
            self.running = False

            self.logger.info("尝试自动点击开始监控按钮...")
            self.logger.info(f"当前开始按钮状态: {self.start_button['state']}")
                
            # 强制点击按钮（即使状态为disabled）
            self.start_button.invoke()
            self.logger.info("已成功触发开始按钮")

        except Exception as e:
            self.logger.error(f"自动点击失败: {str(e)}")
            self.root.after(10000, self.auto_start_monitor)

    def _handle_metamask_popup(self):
        """处理 MetaMask 扩展弹窗的键盘操作"""
        try:
            """屏幕分辨率必须设置为 1920*1080"""
            # 获取主屏幕的宽度和高度
            monitor = get_monitors()[0]  # 获取主屏幕信息
            screen_width, screen_height = monitor.width, monitor.height

            # 计算 "确认" 按钮位置
            confirm_button_x = screen_width - 95  # 同样靠右对齐
            confirm_button_y = 600  # "确认" 按钮通常在下方
            # 点击 "确认" 按钮
            time.sleep(1)
            pyautogui.click(confirm_button_x, confirm_button_y)  

        except Exception as e:
            error_msg = f"处理 MetaMask 扩展弹窗失败: {str(e)}"
            self.logger.error(error_msg)
            raise

    def sleep_refresh(self, operation_name="未指定操作"):
        """
        执行等待3秒并刷新页面的操作,重复1次
        Args:
            operation_name (str): 操作名称,用于日志记录
        """
        try:
            for i in range(2):  # 重复次数，修改数字即可
                time.sleep(3)  # 等待3秒
                self.driver.refresh()    
        except Exception as e:
            self.logger.error(f"{operation_name} - sleep_refresh操作失败: {str(e)}")

    def set_default_price(self, price):
        """设置默认目标价格"""
        try:
            self.default_target_price = float(price)
            self.yes1_price_entry.delete(0, tk.END)
            self.yes1_price_entry.insert(0, str(self.default_target_price))
            self.no1_price_entry.delete(0, tk.END)
            self.no1_price_entry.insert(0, str(self.default_target_price))
            self.logger.info(f"默认目标价格已更新为: {price}")
        except ValueError:
            self.logger.error("价格设置无效，请输入有效数字")

    def send_trade_email(self, trade_type, price, amount, trade_count):
        """发送交易邮件"""
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                hostname = socket.gethostname()
                sender = 'huacaihuijin@126.com'
                receiver = 'huacaihuijin@126.com'
                app_password = 'YUwsXZ8SYSW6RcTf'  # 有效期 180 天，请及时更新，下次到期日 2025-06-29
                
                # 获取交易币对信息
                full_pair = self.trading_pair_label.cget("text")
                trading_pair = full_pair.split('-')[0]
                if not trading_pair or trading_pair == "--":
                    trading_pair = "未知交易币对"
                
                # 根据交易类型选择显示的计数
                count_in_subject = self.sell_count if "Sell" in trade_type else trade_count
                
                msg = MIMEMultipart()
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                subject = f'{hostname}第{count_in_subject}次{trade_type}-{trading_pair}'
                msg['Subject'] = Header(subject, 'utf-8')
                msg['From'] = sender
                msg['To'] = receiver
                
                content = f"""
                交易价格: ${price:.2f}
                交易金额: ${amount:.2f}
                交易时间: {current_time}
                当前买入次数: {self.trade_count}
                当前卖出次数: {self.sell_count}
                """
                msg.attach(MIMEText(content, 'plain', 'utf-8'))
                
                # 使用126.com的SMTP服务器
                server = smtplib.SMTP_SSL('smtp.126.com', 465, timeout=5)  # 使用SSL连接
                server.set_debuglevel(0)
                
                try:
                    server.login(sender, app_password)
                    server.sendmail(sender, receiver, msg.as_string())
                    self.logger.info(f"邮件发送成功: {trade_type}")
                    self.update_status(f"交易邮件发送成功: {trade_type}")
                    return  # 发送成功,退出重试循环
                except Exception as e:
                    self.logger.error(f"SMTP操作失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                    if attempt < max_retries - 1:
                        self.logger.info(f"等待 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)
                finally:
                    try:
                        server.quit()
                    except Exception:
                        pass          
            except Exception as e:
                self.logger.error(f"邮件准备失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)     
        # 所有重试都失败
        error_msg = f"发送邮件失败,已重试{max_retries}次"
        self.logger.error(error_msg)
        self.update_status(error_msg)

    def stop_monitoring(self):
        """停止监控"""
        try:
            self.running = False
            self.stop_event.set()  # 设置停止事件
            # 取消所有定时器
            for timer in [self.url_check_timer, self.login_check_timer, self.refresh_timer]:
                if timer:
                    self.root.after_cancel(timer)
            # 停止URL监控
            if self.url_check_timer:
                self.root.after_cancel(self.url_check_timer)
                self.url_check_timer = None
            # 停止登录状态监控
            if self.login_check_timer:
                self.root.after_cancel(self.login_check_timer)
                self.login_check_timer = None
            
            self.start_button['state'] = 'normal'
            self.stop_button['state'] = 'disabled'
            self.update_status("监控已停止")
            self.set_amount_button['state'] = 'disabled'  # 禁用更新金额按钮
            
            # 将"停止监控"文字变为红色
            self.stop_button.configure(style='Red.TButton')
            # 恢复"开始监控"文字为蓝色
            self.start_button.configure(style='Black.TButton')
            if self.driver:
                self.driver.quit()
                self.driver = None
            # 记录最终交易次数
            final_trade_count = self.trade_count
            self.logger.info(f"本次监控共执行 {final_trade_count} 次交易")

            # 取消页面刷新定时器
            if self.refresh_timer:
                self.root.after_cancel(self.refresh_timer)
                self.refresh_timer = None

        except Exception as e:
            self.logger.error(f"停止监控失败: {str(e)}")

    def update_status(self, message):
        # 检查是否是错误消息
        is_error = any(err in message.lower() for err in ['错误', '失败', 'error', 'failed', 'exception'])
        
        # 更新状态标签，如果是错误则显示红色
        self.status_label.config(
            text=f"Status: {message}",
            foreground='red' if is_error else 'black'
        )
        
        # 错误消息记录到日志文件
        if is_error:
            self.logger.error(message)

    def retry_operation(self, operation, *args, **kwargs):
        """通用重试机制"""
        for attempt in range(self.retry_count):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                self.logger.warning(f"{operation.__name__} 失败，尝试 {attempt + 1}/{self.retry_count}: {str(e)}")
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_interval)
                else:
                    raise

    """以下代码是自动找币功能,从第 2981 行到第 35320 行"""
    # 自动找币第一步:判断是否持仓,是否到了找币时间
    def find_position_label_yes(self):
        """查找Yes持仓标签"""
        max_retries = 2
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                if not self.driver:
                    self.update_status("find_position_label_yes请先连接浏览器")
                    return None
                    
                # 等待页面加载完成
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script('return document.readyState') == 'complete'
                )
                
                # 尝试获取YES标签
                try:
                    position_label_yes = self.driver.find_element(By.XPATH, XPathConfig.POSITION_YES_LABEL)
                    self.logger.info(f"找到了Yes持仓标签: {position_label_yes.text}")
                    
                except Exception:
                    position_label_yes = self._find_element_with_retry(XPathConfig.POSITION_YES_LABEL, timeout=3, silent=True)

                    if position_label_yes:
                        self.logger.info(f"找到了Yes持仓标签: {position_label_yes.text}")
                    else:
                        self.logger.debug("未找到Yes持仓标签")
                        return None
                # 如果找到了标签，返回标签文本
                if position_label_yes:
                    return position_label_yes.text
                else:
                    self.logger.debug("未找到Yes持仓")
                    return None
                         
            except TimeoutException:
                self.logger.debug(f"第{attempt + 1}次尝试未找到YES标签,正常情况!")
            except Exception as e:
                self.logger.debug(f"第{attempt + 1}次尝试发生错误: {str(e)}")
                
            if attempt < max_retries - 1:
                self.logger.info(f"等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)
                self.driver.refresh()
        return None
        
    def find_position_label_no(self):
        """查找No持仓标签"""
        max_retries = 2
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                if not self.driver:
                    self.update_status("find_position_label_no请先连接浏览器")
                    return None
                    
                # 等待页面加载完成
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script('return document.readyState') == 'complete'
                )
                
                # 尝试获取NO标签
                try:
                    position_label_no = self.driver.find_element(By.XPATH, XPathConfig.POSITION_NO_LABEL)
                    self.logger.info(f"找到了No持仓标签: {position_label_no.text}")
                    
                except Exception:
                    position_label_no = self._find_element_with_retry(XPathConfig.POSITION_NO_LABEL, timeout=3, silent=True)

                    if position_label_no:
                        self.logger.info(f"找到了No持仓标签: {position_label_no.text}")
                    else:
                        self.logger.debug("未找到No持仓标签")
                        return None
                # 如果找到了标签，返回标签文本
                if position_label_no:
                    return position_label_no.text
                else:
                    self.logger.debug("未找到No持仓")
                    return None
                               
            except TimeoutException:
                self.logger.warning(f"第{attempt + 1}次尝试未找到NO标签")
            except Exception as e:
                self.logger.error(f"第{attempt + 1}次尝试发生错误: {str(e)}")
                
            if attempt < max_retries - 1:
                self.logger.info(f"等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)
                self.driver.refresh()
        return None
    
    def is_auto_find_54_coin_time(self):
        """判断是否处于自动找币时段(周六2点至周五20点)"""
        try:
            beijing_tz = timezone(timedelta(hours=8))
            now = datetime.now(timezone.utc).astimezone(beijing_tz)
            
            # 周六判断（weekday=5）
            if now.weekday() == 5:
                # 周六2点至23:59
                if now.hour >= 2:
                    self.logger.info("✅ 当前处于找币时段")
                    return True
            
            # 周日至周五判断（weekday=6到4）
            elif now.weekday() in (6,0,1,2,3,4):
                # 全天有效直到周五20点
                if now.hour < 20 or (now.weekday() != 4 and now.hour >= 20):
                    self.logger.info("✅ 当前处于找币时段")
                    return True
            
            return False
        except Exception as e:
            self.logger.error(f"找币时间判断异常: {str(e)}")
            return False
        
    # 是否持仓
    def is_position_yes_or_no(self):
        self.logger.info("检查当前是否持仓")
        try:
            # 同时检查Yes/No两种持仓标签
            self.yes_element = self.find_position_label_yes()
            self.no_element = self.find_position_label_no()

            full_pair = self.trading_pair_label.cget("text")
            trading_pair = full_pair.split('-above')[0]

            # 任一标签显示持仓状态即返回True
            if (self.yes_element and self.yes_element=="Yes") or (self.no_element and self.no_element=="No"):
                self.logger.info(f"检测到持仓状态,持仓为{trading_pair}:{self.yes_element}或{self.no_element}")
                return True
            elif self.yes_element is None and self.no_element is None:
                return False
            else:
                return False    
            
        except Exception as e:
            self.logger.error(f"持仓检查异常: {str(e)}")

        return True
    
    def contrast_portfolio_cash(self):
        """对比持仓币对和现金"""
        try:
            try:
                # 检查portfolio_value和cash_value是否已经存在并且是字符串
                if hasattr(self, 'portfolio_value') and hasattr(self, 'cash_value'):
                    # 尝试将字符串转换为数值
                    if isinstance(self.portfolio_value, str):
                        portfolio_text = self.portfolio_value.replace("$", "").replace(",", "").strip()
                        portfolio_value = float(portfolio_text) if portfolio_text else 0 
                    else:
                        portfolio_value = self.portfolio_value
                    
                    if isinstance(self.cash_value, str):
                        cash_text = self.cash_value.replace("$", "").replace(",", "").strip()
                        cash_value = float(cash_text) if cash_text else 0  
                    else:
                        cash_value = self.cash_value
                    
                    value = round(portfolio_value - cash_value, 2)
                    
                    if value > 0.6:
                        self.logger.info(f"{value}>0,✅ 有持仓")
                        return True
                    else:
                        self.logger.info(f"{value}=0,❌ 无持仓")
                        return False
                else:
                    self.logger.warning("portfolio_value或cash_value不存在,无法对比")
                    return False
            except Exception as inner_e:
                self.logger.error(f"处理portfolio和cash值失败: {str(inner_e)}")
                return False
        except Exception as e:
            self.logger.error(f"持仓币对和现金对比异常: {str(e)}")
            return False

    def start_auto_find_coin(self):
        """启动自动找币"""
        if self.login_running:
            self.logger.info("正在登录,退出自动找币")
            return

        if self.contrast_portfolio_cash():
            self.stop_url_monitoring()
            self.stop_refresh_page()
            self.start_auto_find_coin_running = True

            # 有持仓,点击 PORTFOLIO_BUTTON按钮,打开币对
            try: 
                portfolio_button = self.driver.find_element(By.XPATH, XPathConfig.PORTFOLIO_BUTTON)
                portfolio_button.click()
                time.sleep(1)
            except Exception as e: 
                # 尝试使用_find_element_with_retry方法
                try:
                    portfolio_button = self._find_element_with_retry(
                        XPathConfig.PORTFOLIO_BUTTON,
                        timeout=3,
                        silent=True
                    )
                    if portfolio_button:
                        portfolio_button.click()
                        time.sleep(1)
                    else:
                        self.logger.error("无法找到Portfolio按钮")
                        return False
                except Exception as retry_e:
                    self.logger.error(f"使用retry方法点击Portfolio按钮失败: {str(retry_e)}")
                    return False
                
            # 点击 FIND_PORTFOLIO_COIN_BUTTON按钮,打开持仓详情页
            try:
                find_portfolio_coin_button = self.driver.find_element(By.XPATH, XPathConfig.FIND_PORTFOLIO_COIN_BUTTON)
                find_portfolio_coin_button.click()
                
            except Exception as e: 
                # 尝试使用_find_element_with_retry方法
                try:
                    find_portfolio_coin_button = self._find_element_with_retry(
                        XPathConfig.FIND_PORTFOLIO_COIN_BUTTON,
                        timeout=3,
                        silent=True
                    )
                    if find_portfolio_coin_button:
                        find_portfolio_coin_button.click()
                        
                    else:
                        self.logger.error("无法找到FIND_PORTFOLIO_COIN_BUTTON按钮")
                        return False
                except Exception as retry_e:
                    self.logger.error(f"使用retry方法点击FIND_PORTFOLIO_COIN_BUTTON按钮失败: {str(retry_e)}")
                    return False

            time.sleep(5)
            
            # 保存当前 URL 到 config
            base_url = self.driver.current_url
            current_url = self.extract_base_url(base_url)
            self.config['website']['url'] = current_url
            self.save_config()
            self.logger.info(f"已保存{current_url}到config.json")

            # 把保存到config的url放到self.url_entry中
            # 保存前,先清除现有的url
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, current_url)
            self.target_url = self.url_entry.get()

            time.sleep(2)
            self.start_url_monitoring()
            self.refresh_page()
            self.start_auto_find_coin_running = False
            self.stop_auto_find_coin()
        # 没有持仓就判断是否到了找币时间
        else:
            if self.is_auto_find_54_coin_time():
                # 使用线程执行登录检查，避免阻塞主线程
                self.auto_find_coin_timer = self.root.after(0, self.find_54_coin)
            else:
                self.logger.info("当前不处于自动找币时段")
                self.start_auto_find_coin_running = False

    def find_54_coin(self):
        """自动找币,线程名:self.auto_find_coin_timer"""
        self.logger.info("✅ 当前没有持仓,开始自动找币")
        try:
            self.stop_url_monitoring()
            self.stop_refresh_page()
            self.start_auto_find_coin_running = True

            # 保存原始窗口句柄，确保在整个过程中有一个稳定的引用
            self.original_window = self.driver.current_window_handle
            
            # 设置搜索关键词
            coins = [
                'BTC',
                'ETH',
                'SOL',
                'XRP'
            ]
            for coin in coins:
                try:  # 为每个币种添加单独的异常处理
                    if self.login_running:
                        self.logger.info("正在登录,退出自动找币")
                        return
                    coin_new_weekly_url = self.find_new_weekly_url(coin)
                    
                    if coin_new_weekly_url:
                        self.driver.get(coin_new_weekly_url)

                        # 获取Yes和No的价格
                        prices = self.driver.execute_script("""
                            function getPrices() {
                                const prices = {yes: null, no: null};
                                const elements = document.getElementsByTagName('span');
                                
                                for (let el of elements) {
                                    const text = el.textContent.trim();
                                    if (text.includes('Yes') && text.includes('¢')) {
                                        const match = text.match(/(\\d+\\.?\\d*)¢/);
                                        if (match) prices.yes = parseFloat(match[1]);
                                    }
                                    if (text.includes('No') && text.includes('¢')) {
                                        const match = text.match(/(\\d+\\.?\\d*)¢/);
                                        if (match) prices.no = parseFloat(match[1]);
                                    }
                                }
                                return prices;
                            }
                            return getPrices();
                        """)

                        if prices['yes'] is not None and prices['no'] is not None:
                            yes_price = float(prices['yes'])
                            no_price = float(prices['no'])

                        # 判断 YES 和 NO 价格是否在 48-56 之间
                        if (46 <= yes_price <= 56) or (46 <= no_price <= 56):
                            # 保存当前 URL 到 config
                            self.config['website']['url'] = coin_new_weekly_url
                            self.save_config()
                            self.logger.info(f"{coin}: YES {int(yes_price)}¢|NO {int(no_price)}¢ ✅ 符合要求,已保存到 config")

                            # 清除url_entry中的url
                            self.url_entry.delete(0, tk.END)
                            # 把保存到config的url放到self.url_entry中
                            self.url_entry.insert(0, coin_new_weekly_url)

                            self.target_url = self.url_entry.get()
                            self.logger.info(f"✅ {self.target_url} 已插入到主界面上")
                            self.start_url_monitoring()
                            self.refresh_page()
                            self.stop_auto_find_coin()  
                            return
                        else:
                            self.logger.info(f"{coin}: YES {int(yes_price)}¢|NO {int(no_price)}¢ ❌ 不符合要求")           

                except Exception as e:
                    self.logger.error(f"处理{coin}时出错: {str(e)}")
                    # 尝试恢复到原始窗口并继续下一个币种
                    try:
                        # 切换回原始窗口
                        self.driver.switch_to.window(self.original_window)
                    except Exception as inner_e:
                        self.logger.error(f"恢复窗口时出错: {str(inner_e)}")
                        # 如果无法恢复，可能需要重新创建浏览器会话
                        self._start_browser_monitoring(self.target_url)
                        break  # 中断循环，避免继续出错
            
            self.root.after(5000, self.start_url_monitoring)
            self.start_auto_find_coin_running = False
            # 增加 10 分钟后再次找币
            self.root.after(self.refresh_interval, self.start_auto_find_coin)
            self.logger.info("10分钟后再次找币")

        except Exception as e:
            self.logger.error(f"自动找币异常: {str(e)}")
            self.root.after(self.refresh_interval, self.start_auto_find_coin)

    def stop_auto_find_coin(self):
        """停止自动找币"""
        try:
            # 取消定时器
            if hasattr(self, 'auto_find_coin_timer') and self.auto_find_coin_timer:
                self.root.after_cancel(self.auto_find_coin_timer)
                self.auto_find_coin_timer = None
                self.logger.info("✅ 自动找币定时器已取消")
            else:
                self.logger.info("自动找币未在运行中,无需停止")
            # 设置标志位，让循环内部可以检测到停止信号
            self.start_auto_find_coin_running = False  
            self.stop_auto_find_running = True
            self.logger.info("❌ 自动找币已停止")
        except Exception as e:
            self.logger.error(f"停止自动找币时发生错误: {str(e)}")
            self.stop_auto_find_running = True

    def find_new_weekly_url(self, coin):
        """在Polymarket市场搜索指定币种的周合约地址,只返回周合约地址"""
        try:
            if self.trading:
                return

            if self.login_running:
                self.logger.info("正在登录,退出自动找币")
                return
                
            # 保存当前窗口句柄作为局部变量，用于本方法内部使用
            original_tab = self.driver.current_window_handle

            # 重置所有按钮样式为蓝色
            for btn in [self.btc_button, self.eth_button, self.solana_button, 
                    self.xrp_button]:
                btn.configure(style='Blue.TButton')
            
            # 设置被点击的按钮为红色
            if coin == 'BTC':
                self.btc_button.configure(style='Red.TButton')
            elif coin == 'ETH':
                self.eth_button.configure(style='Red.TButton')
            elif coin == 'SOL':
                self.solana_button.configure(style='Red.TButton')
            elif coin == 'XRP':
                self.xrp_button.configure(style='Red.TButton')

            base_url = "https://polymarket.com/markets/crypto?_s=start_date%3Adesc"
            self.driver.switch_to.new_window('tab')
            self.driver.get(base_url)

            # 定义search_tab变量，保存搜索标签页的句柄
            search_tab = self.driver.current_window_handle

            # 等待页面加载完成
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(2)  # 等待页面渲染完成
            
            # 设置搜索关键词
            link_text_map = {
                'BTC': 'Bitcoin above',
                'ETH': 'Ethereum above',
                'SOL': 'Solana above',
                'XRP': 'Ripple above'
            }
            search_text = link_text_map.get(coin, '')
            
            if not search_text:
                self.logger.error(f"无效的币种: {coin}")
                # 关闭搜索标签页
                self.driver.close()
                # 切换回原始窗口
                self.driver.switch_to.window(original_tab)
                return None
            try:
                # 使用确定的XPath查找搜索框
                try:
                    search_box = self.driver.find_element(By.XPATH, XPathConfig.SEARCH_INPUT)
                except Exception as e:
                    search_box = self._find_element_with_retry(
                        XPathConfig.SEARCH_INPUT,
                        timeout=3,
                        silent=True
                    )
                
                # 创建ActionChains对象
                actions = ActionChains(self.driver)
                
                # 清除搜索框并输入搜索词
                search_box.clear()
                search_box.send_keys(search_text)
                # time.sleep(1)  # 等待搜索词输入完成
                
                # 按ENTER键开始搜索
                actions.send_keys(Keys.RETURN).perform()
                time.sleep(2)  # 等待搜索结果加载
                
                try:
                    # 点击 seach_confirm_button按钮 
                    search_confirm_button = self.driver.find_element(By.XPATH, XPathConfig.SEARCH_CONFIRM_BUTTON)
                    self.logger.info(f"点击SEARCH_CONFIRM_BUTTON按钮: {search_confirm_button}")
                    search_confirm_button.click()
                except Exception as e: 
                    # 尝试使用_find_element_with_retry方法
                    try:
                        search_confirm_button = self._find_element_with_retry(
                            XPathConfig.SEARCH_CONFIRM_BUTTON,
                            timeout=3,
                            silent=True
                        )

                        if search_confirm_button:
                            search_confirm_button.click()   
                        else:
                            self.logger.error("无法找到SEARCH_CONFIRM_BUTTON按钮")
                            return False
                    except Exception as retry_e:
                        self.logger.error(f"使用retry方法点击SEARCH_CONFIRM_BUTTON按钮失败: {str(retry_e)}")
                        return False
                
                # 使用正确的组合键（Windows/Linux用Ctrl+Enter，Mac用Command+Enter）
                modifier_key = Keys.COMMAND if sys.platform == 'darwin' else Keys.CONTROL
                
                # 创建动作链
                actions = ActionChains(self.driver)
                actions.key_down(modifier_key).send_keys(Keys.ENTER).key_up(modifier_key).perform()
                
                # 切换到新标签页获取完整URL
                time.sleep(2)  # 等待新标签页打开
        
                # 获取所有窗口句柄
                all_handles = self.driver.window_handles
                
                # 切换到最新打开的标签页
                if len(all_handles) > 2:  # 原始窗口 + 搜索标签页 + coin标签页
                    
                    self.driver.switch_to.window(all_handles[-1])
                    WebDriverWait(self.driver, 20).until(EC.url_contains('/event/'))
                    
                    # 获取当前URL
                    new_weekly_url = self.driver.current_url
                    time.sleep(10)
                    # 这里如果价格是 54,那么会触发自动交易
                    if self.trading == True:
                        time.sleep(50)
                        # 保存当前 URL 到 config
                        self.config['website']['url'] = new_weekly_url
                        self.save_config()
                        self.logger.info(f"✅ {coin}:符合要求, 正在交易,已保存到 config")
                        
                        # 把保存到config的url放到self.url_entry中
                        # 保存前,先清楚现有的url
                        self.url_entry.delete(0, tk.END)
                        self.url_entry.insert(0, new_weekly_url)
                        self.target_url = self.url_entry.get()
                        self.logger.info(f"✅ {self.target_url}:已插入到主界面上")

                        self.target_url_window = self.driver.current_window_handle
                        time.sleep(3)

                        # 关闭原始和搜索窗口
                        self.driver.switch_to.window(search_tab)
                        self.driver.close()
                        self.driver.switch_to.window(original_tab)
                        self.driver.close()
                        self.driver.switch_to.window(self.target_url_window)

                        self.start_url_monitoring()
                        self.refresh_page()
                        self.stop_auto_find_coin()

                        return False
                    else:
                        # 关闭当前详情URL标签页
                        self.driver.close()
                        
                        # 切换回搜索标签页
                        self.driver.switch_to.window(search_tab)
                        
                        # 关闭搜索标签页
                        self.driver.close()
                        
                        # 切换回原始窗口
                        self.driver.switch_to.window(original_tab)
                        
                        return new_weekly_url
                else:
                    self.logger.warning(f"未能打开{coin}的详情页")
                    # 关闭搜索标签页
                    self.driver.close()
                    # 切换回原始窗口
                    self.driver.switch_to.window(original_tab)
                    return None
                
            except NoSuchElementException as e:
                self.logger.warning(f"未找到{coin}周合约链接: {str(e)}")
                # 关闭搜索标签页
                self.driver.close()
                # 切换回原始窗口
                self.driver.switch_to.window(original_tab)
                return None
            
        except Exception as e:
            self.logger.error(f"操作失败: {str(e)}")
        
    def _find_element_with_retry(self, xpaths, timeout=3, silent=False):
        """优化版XPATH元素查找(增强空值处理)"""
        try:
            for i, xpath in enumerate(xpaths, 1):
                try:
                    element = WebDriverWait(self.driver, timeout).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    return element
                except TimeoutException:
                    if not silent:
                        self.logger.warning(f"第{i}个XPATH定位超时: {xpath}")
                    continue
        except Exception as e:
            if not silent:
                raise
        return None
    
    def extract_base_url(self, url):
        """
        将URL分隔成两部分,返回第一部分基础URL
        例如：从 https://polymarket.com/event/dogecoin-above-0pt20-on-march-14/dogecoin-above-0pt20-on-march-14?tid=1741406505993
        提取 https://polymarket.com/event/dogecoin-above-0pt20-on-march-14
        """
        try:
            # 先按 "?" 分割，去掉查询参数
            base_url = url.split('?')[0]

            # 再按 "/" 进行分割，去掉最后一部分重复的路径
            clean_url = base_url.rsplit('/', 1)[0]
            
            return clean_url
            
        except Exception as e:
            self.logger.error(f"提取基础URL时出错: {str(e)}")
            return url
        
    def run(self):
        """启动程序"""
        try:
            self.logger.info("启动主程序...")
            self.root.mainloop()
        except Exception as e:
            self.logger.error(f"程序运行出错: {str(e)}")
            raise

if __name__ == "__main__":
    try:
        # 打印启动参数，用于调试
        print("启动参数:", sys.argv)
        
        # 初始化日志
        logger = Logger("main")
        logger.info(f"程序启动，参数: {sys.argv}")
        
        # 检查是否是重启模式
        is_restart = '--restart' in sys.argv
        if is_restart:
            logger.info("检测到--restart参数")
            
        # 创建并运行主程序
        app = CryptoTrader()
        app.root.mainloop()
        
    except Exception as e:
        print(f"程序启动失败: {str(e)}")
        if 'logger' in locals():
            logger.error(f"程序启动失败: {str(e)}")
        sys.exit(1)
    
