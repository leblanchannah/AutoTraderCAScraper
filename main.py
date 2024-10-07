import requests
from bs4 import BeautifulSoup
import pandas as pd 
import plotly.express as px



def split_title(title):
    data = {
        'year':"",
        'make':"",
        'model':"",
        'trim':"",
    }
    if title:
        title = title.split(" ")
        data['year'] = title[0]
        data['make'] = title[1]
        data['model'] = title[2]
    return data

    
def clean_text(dom_element):
    if dom_element:
        return " ".join(dom_element.text.split())


def parse_search_result(soup):
    title = soup.find('span', class_='title-with-trim')
    title = clean_text(title)
    title_details = split_title(title)
    proximity = soup.find('span', class_='proximity-text')
    details = soup.find('p', class_='details used')
    odometer = soup.find('span', class_='odometer-proximity')
    price = soup.find('span', class_='price-amount')
    price_delta = soup.find('div', class_='price-delta')
    dealer = soup.find('div', class_='dealer-inner-area')
    url = soup.find("a", class_="detail-price-area").get("href")

    search_entry = {
        'title':title,
        'proximity':clean_text(proximity),
        'odometer':clean_text(odometer),
        'price':clean_text(price),
        'details':clean_text(details),
        'price_delta':clean_text(price_delta),
        'dealer':clean_text(dealer),
        'listing':url
    }
    return {**search_entry, **title_details}

def search_sales(make, model, city, province, postal_code, n_records=100, page=0):

    url = f"https://www.autotrader.ca/cars/{make}/{model}/{province}/{city}/?rcp={n_records}&rcs={page}&srt=35&prx=100&prv=Ontario&loc={postal_code}&hprc=True&wcp=True&sts=New-Used&inMarket=basicSearch"
    print(url)
    payload = {}
    headers = {
    'accept-language': 'en-US,en;q=0.9',
    'origin': 'https://www.autotrader.ca',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    }

    response = requests.request("GET", url, headers=headers, data=payload)
    print(response)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    return soup

def main():
    search_results = []
    
    soup = search_sales('honda', 'cr-v', 'toronto','on', postal_code='M5W%201E6', n_records=100, page=0)
    search_results.append(soup)
    # https://www.autotrader.ca/cars/honda/cr-v/on/ottawa/?rcp=15&rcs=0&srt=35&prx=100&prv=Ontario&loc=K1Y%201S3&hprc=True&wcp=True&sts=New-Used&adtype=Dealer&inMarket=advancedSearch
    with open("crv_search_p0.html", "w") as file:
            file.write(str(soup))


    num_results = soup.find('span', id='titleCount').text
    num_results = int(num_results.replace(',', ''))
    # pages = len(soup.find_all('li', class_='page-item'))
    # print(f"pages:{pages}")
    viewed = 100
    while viewed <= num_results:
        page = int(viewed/100)
        soup = search_sales('honda', 'cr-v', 'toronto','on', postal_code='M5W%201E6', n_records=100, page=page)
        search_results.append(soup)
        with open(f"crv_search_p{viewed}.html", "w") as file:
            file.write(str(soup))
        viewed+=100


    print(len(search_results))

    # with open("crv_search.html") as fp:
    #     soup = BeautifulSoup(fp, 'html.parser')
    data = []
    for soup in search_results:
        print('new_page')
        result_items = soup.find_all('div', class_='result-item')

        for item in result_items:
            search_result = parse_search_result(item)
            data.append(search_result)

    df = pd.DataFrame(data)
    print(df.head())
    print(df.columns)

    # df['year'] = df['year'].astype(int)
    df['odometer'] = df['odometer'].str.replace("[^0-9]","",regex=True).astype(float)
    df['price'] = df['price'].str.replace("[^0-9]","",regex=True).astype(float)

    df.to_csv('search_test.csv')



df = pd.read_csv('search_test.csv')

fig = px.scatter(df, y="price", x="odometer", color="year")
fig.update_traces(marker_size=10)
fig.update_layout(scattermode="group", scattergap=0.75)
fig.show()
