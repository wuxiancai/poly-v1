"""
XPATH配置文件
用于集中管理所有XPATH路径
修改XPATH时只需要在此文件中更新对应的值
"""

class XPathConfig:
    # 1.登录相关，长期有效
    LOGIN_BUTTON = [
        '//button[contains(text(), "Log In")]',
        '//button[@class="c-gBrBnR c-gBrBnR-gDWzxt-variant-primary c-gBrBnR-bxvuTL-fontWeight-medium c-gBrBnR-dRRWyf-fontSize-md c-gBrBnR-gFoOfa-cv c-gBrBnR-ikLDqfK-css"]'
        
    ]
    # 2.Metamask相关，长期有效
    METAMASK_BUTTON = [
        '//*[@id="authentication-modal"]/div/div[2]/div/div/div/div/div[3]/button[1]'
    ]

    # 3.Buy按钮长期有效
    BUY_BUTTON = [
        '//button[(text()="Buy")]', 
        '/html/body/div[1]/div[2]/div/div/div/div/div/div[1]/div[1]/div/div/button[1]'
    ]

    # 4.Buy Yes 按钮长期有效
    BUY_YES_BUTTON = [
        '//button[.//span[contains(text(), "Yes")] and .//span[contains(text(), "¢")]]',
        '/html/body/div[1]/div[2]/div/div/div/div/div/div[1]/div[2]/div[1]/span[1]/button'
    ]

    # 5.Buy No 按钮长期有效
    BUY_NO_BUTTON = [
        '//button[.//span[contains(text(), "No")] and .//span[contains(text(), "¢")]]',
        '/html/body/div[1]/div[2]/div/div/div/div/div/div[1]/div[2]/div[1]/span[2]/button'
    ]

    # 6.Sell Yes 按钮长期有效
    SELL_YES_BUTTON = [
        '//button[.//span[contains(text(), "Yes")] and .//span[contains(text(), "¢")]]',
        '/html/body/div[1]/div[2]/div/div/div/div/div/div[1]/div[2]/div[1]/span[1]/button'
       
    ]

    # 7.Sell No 按钮长期有效
    SELL_NO_BUTTON = [
        '//button[.//span[contains(text(), "No")] and .//span[contains(text(), "¢")]]',
        
    ]

    # 8.Buy-确认买入按钮
    BUY_CONFIRM_BUTTON = [
        '//button[@class="c-bDcLpV c-bDcLpV-fLyPyt-color-blue c-bDcLpV-ileGDsu-css"]',
        '//button[.//span[contains(text(), "B")] and .//span[contains(text(), "u")] and .//span[contains(text(), "y")] and .//span[contains(text(), "Y")] and .//span[contains(text(), "e")] and .//span[contains(text(), "s")]]',
        '//button[.//span[contains(text(), "B")] and .//span[contains(text(), "u")] and .//span[contains(text(), "y")] and .//span[contains(text(), "N")] and .//span[contains(text(), "o")]',
        '//button[contains(text(), "Buy Yes") or contains(text(), "Buy No")]',
        '//button[contains(text(), "Buy" and contains(text(), "Yes")) or contains(text(), "Buy" and contains(text(), "No"))]'
    ]

    # 9.Sell-卖出按钮
    SELL_PROFIT_BUTTON = [
        '//button[@class="c-bDcLpV c-bDcLpV-fLyPyt-color-blue c-bDcLpV-ileGDsu-css"]',
        '/html/body/div[1]/div[2]/div/div/div/div/div/div[1]/div[3]/div[2]/div/span/button',
        '//button[.//span[contains(text(), "S")] and .//span[contains(text(), "e")] and .//span[contains(text(), "l")] and .//span[contains(text(), "l")]and .//span[contains(text(), "N")] and .//span[contains(text(), "o")]',
        '//button[.//span[contains(text(), "S")] and .//span[contains(text(), "e")] and .//span[contains(text(), "l")] and .//span[contains(text(), "l")] and .//span[contains(text(), "Y")] and .//span[contains(text(), "e")] and .//span[contains(text(), "s")]]',
        '//button[contains(text(), "Sell Yes") or contains(text(), "Sell No")]',
        '//button[contains(text(), "Sell" and contains(text(), "Yes")) or contains(text(), "Sell" and contains(text(), "No"))]'
    ]

    # 10.Amount输入框长期有效
    AMOUNT_INPUT = [
        '//input[@id="market-order-amount-input"]',
        '//p[text()="Amount"]/ancestor::div//input[@placeholder="$0"]',
        '/html/body/div[1]/div[2]/div/div/div/div/div/div[1]/div[3]/div/div/div/div/div[1]/div/div[1]/div[2]/div/div/input'
    ]

    # 11.Position-Yes标签长期有效
    POSITION_YES_LABEL = [
        '//div[text()="Yes"]',
        '//div[@class="c-dhzjXW c-chKWaB c-chKWaB-eVTycx-color-green c-dhzjXW-ibxvuTL-css" and text()="Yes"]'
    ]

    # 12.Position-No标签长期有效
    POSITION_NO_LABEL = [
        '//div[text()="No"]',
        '//div[@class="c-dhzjXW c-chKWaB c-chKWaB-kNNGp-color-red c-dhzjXW-ibxvuTL-css" and text()="No"]'
    ]

    # 13.Position-Yes值长期有效
    POSITION_YES_VALUE = [
        '(//span[@class="c-PJLV c-dnafHo"])[1]',
        '/html/body/div[1]/div[2]/div/div/main/div/div/div/div/div/div[3]/div/div[2]/div/div[2]/table/tbody/tr[1]/td[4]/span[2]',
        '//*[@id="event-detail-container"]/div/div[3]/div/div[2]/div/div[2]/table/tbody/tr[1]/td[4]/span[2]'
    ]

    # 14.Position-No值长期有效
    POSITION_NO_VALUE = [
        '(//span[@class="c-PJLV c-dnafHo"])[2]',
        '/html/body/div[1]/div[2]/div/div/main/div/div/div/div/div/div[3]/div/div[2]/div/div[2]/table/tbody/tr[2]/td[4]/span[2]'
    ]

    # 15.Position-Sell按钮长期有效
    POSITION_SELL_BUTTON = [
        '//button[@class="c-gBrBnR c-gBrBnR-iifsICY-css"]',
        '//td//div//button[text()="Sell"]', 
    ]

    # 16.Position-Sell Yes按钮 长期有效
    POSITION_SELL_YES_BUTTON = [
        '(//button[@class="c-gBrBnR c-gBrBnR-iifsICY-css"])[1]',
        '(//td//div//button[text()="Sell"])[1]'
        ]

    # 17.Position-Sell No按钮长期有效
    POSITION_SELL_NO_BUTTON = [
        '(//button[@class="c-gBrBnR c-gBrBnR-iifsICY-css"])[2]',
        '(//td//div//button[text()="Sell"])[2]'
        ]

    # 18.Portfolio值长期有效
    PORTFOLIO_VALUE = [
        '//button[@href="/portfolio"]//p[contains(text(), "$")]',
        '//a[@href="/portfolio"]//span[contains(text(), "$")]'
    ]

    # 19.Cash值长期有效
    CASH_VALUE = [
        '//button[.//p[text()="Cash"]]/p[contains(text(), "$")]',
        '//button[.//span[text()="Cash"]]/span[contains(text(), "$")]'
    ]

    # 20.History-交易记录长期有效
    HISTORY = [
        '(//div[@class="PJLV PJLV-ihovmxi-css"])[1]',
        '(//div[@class="PJLV PJLV-ihovmxi-css"]//p)[1]', 
        '/html/body/div[1]/div[2]/div/div/main/div/div/div/div/div/div[3]/div/div[5]/div/div[2]/div/p'  
    ]
    
    # 21.搜索框长期有效
    SEARCH_INPUT = [
        '//input[@id="markets-grid-search-input"]',
        '/html/body/div[1]/div[2]/div/div/main/div/div/div[3]/div/div/div/div[1]/div[2]/div[2]/input',
        'input[placeholder="Search by market"]'
    ] 

    # 22.Portfolio_button长期有效
    PORTFOLIO_BUTTON = [
        '//button[@href="/portfolio"]',
        '//a[@href="/portfolio"]' 
    ]

    # 23.FIND_PORTFOLIO_COIN_BUTTON长期有效
    FIND_PORTFOLIO_COIN_BUTTON = [
        '//a[contains(text(), "above")]' 
    ]

    # 24.search_confirm_button长期有效
    SEARCH_CONFIRM_BUTTON = [
        '//p[contains(text(), "above")]', 
        '//a//p[contains(text(), "above")]' 
    ]
