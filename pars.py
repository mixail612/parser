from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.service import Service


chromedriver_path = ''
with open('config.txt', 'r', encoding='UTF-8') as f:
    lines = f.readlines()
    chromedriver_path = lines[5].split(': ')[1]


def pars(url, parse_to, gui):  # получение новых объявлений по ссылке
    parsing = 1
    while parsing:  # получение станицы
        try:
            service = Service(executable_path=chromedriver_path)
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--window-size=1920x1080")
            browser = webdriver.Chrome(service=service, options=chrome_options)
            browser.get(url)
            parsing = 0
        except BaseException as ex:
            print(ex)
            parsing = 1

    soup = BeautifulSoup(browser.page_source)
    advs = soup.find_all('div', {'class': ['iva-item-root-_lk9K']})
    advs_list = []
    for adv in advs:
        if adv:
            adv = adv.div.div
            if adv:
                adv = adv.div.next_sibling.div  # получение объявления
                advs_list.append({})
                for _ in range(7):
                    if adv:
                        cl = adv['class']
                        if not cl:
                            continue
                        if 'iva-item-titleStep' in cl[0]:
                            print('https://www.avito.ru' + adv.a['href'] + ' ' + str(parse_to))
                            # проверка на то, является ли объявление старым
                            if 'https://www.avito.ru' + adv.a['href'] in parse_to:
                                return advs_list[:-1]
                            advs_list[-1]['url'] = 'https://www.avito.ru' + adv.a['href']
                            advs_list[-1]['title'] = adv.text
                        if 'iva-item-priceStep' in cl[0]:
                            advs_list[-1]['price'] = adv.text
                        if 'iva-item-autoParamsStep' in cl[0]:
                            advs_list[-1]['params'] = adv.text
                        if 'iva-item-descriptionStep' in cl[0]:
                            advs_list[-1]['description'] = adv.text
                        adv = adv.next_sibling
    if advs_list:
        return advs_list
