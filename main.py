import requests
from bs4 import BeautifulSoup
import pandas as pd 
import plotly.express as px
import statsmodels.api as sm
import time

from statsmodels.formula.api import ols

def split_title(title):
    if title:
        title = title.split(" ")
        data = {
            'year':title[0],
            'make':title[1],
            'model':title[2],
        }
        return data

    
def clean_text(dom_element):
    if dom_element:
        return " ".join(dom_element.text.split())


def parse_search_result(soup):
    try:
        item_id = soup.get('id')
    except KeyError as e:
        print("Unable to get id from")
        print(e)
        item_id = None

    title = soup.find('span', class_='title-with-trim')
    title = clean_text(title)
    title_details = split_title(title)
    proximity = soup.find('span', class_='proximity-text')
    details = soup.find('p', class_='details used')
    odometer = soup.find('span', class_='odometer-proximity')
    price = soup.find('span', class_='price-amount')
    price_delta = soup.find('div', class_='price-delta-text')
    dealer = soup.find('div', class_='dealer-inner-area')
    url = soup.find("a", class_="detail-price-area").get("href")

    search_entry = {
        'id':item_id,
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

def get_search(make, model, province, postal_code, n_records=100, page=0):
    url = f"https://www.autotrader.ca/cars/{make}/{model}/{province}/?rcp={n_records}&rcs={page}&srt=35&prx=100&prv=Ontario&loc={postal_code}&hprc=True&wcp=True&sts=New-Used&adtype=Dealer&inMarket=advancedSearch"
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


def advanced_search(make, model, province, postal_code, max_results):
    search_results = []
    # send first request to get total number of available listings - used for sending requests by page
    soup = get_search(make, model, province, postal_code=postal_code, n_records=100, page=0)
    soup_result_items = soup.find_all('div', class_='result-item')
    search_results.extend(soup_result_items)

    num_results = soup.find('span', id='titleCount').text
    num_results = int(num_results.replace(',', ''))
    print(f'Num results in search {num_results}')

    viewed = len(soup)
    while viewed <= num_results and viewed <= max_results:
        time.sleep(5)
        page = int(viewed/100)
        soup = get_search(make, model, province, postal_code=postal_code, n_records=100, page=page)
        search_results.extend(soup.find_all('div', class_='result-item'))
        viewed+=100

    print(f'found {len(search_results)} results')

    data = []
    for item in search_results:
        search_result = parse_search_result(item)
        data.append(search_result)

    df = pd.DataFrame(data)

    df['odometer'] = df['odometer'].str.replace("[^0-9]","",regex=True).astype(float)
    df['price'] = df['price'].str.replace("[^0-9]","",regex=True).astype(float)

    return df

def ols_by_model(df):
    for model_name, data in df.groupby("model"):
        print(model_name)

        X = data[['km_k', 'year']]  # Independent variables
        X = sm.add_constant(X)        # Adds a constant term to the predictor
        y = data['price']  

        model = sm.OLS(y, X).fit()
        print(model.summary())
        with open(f'ols_summary_{model_name}.txt', 'w') as fh:
            fh.write(model.summary().as_text())


if __name__ == "__main__":
    # postal_code = 'M5W%201E6'
    # province = 'on'
    # max_results = 2000

    # df_crv = advanced_search('honda', 'cr-v', province, postal_code, max_results)
    # df_rav4 = advanced_search('toyota', 'rav4', province, postal_code, max_results)
    # df_forester = advanced_search('subaru', 'forester', province, postal_code, max_results)
    # df_q3 = advanced_search('audi', 'q3', province, postal_code, max_results)

    # df = pd.concat([df_crv, df_rav4, df_forester, df_q3])
    # df.to_csv('search_test.csv')

    df = pd.read_csv('search_test.csv')

    df['km_k'] = df['odometer'] / 1000.0

    df = df.dropna(subset=['odometer','year','price'], axis=0, how='any')
    df['mileage_per_yr'] = df.groupby(['model','year'])['km_k'].transform('mean')
    df['price_per_km'] = df['price'] / df['km_k']



    # fig = px.scatter(df, y="price", x="km_k", color="year", facet_col="model", trendline='ols', trendline_color_override="black")
    # fig.update_traces(marker_size=8)
    # fig.update_layout(
    #     title='AutoTraderCa search results on 20/10/2024',
    #     yaxis_title="Price (CAD)"    
    # )
    # fig.update_xaxes(title="Mileage (km)")
    
    # fig.show()
    # fig.write_image("model_comparison_mileage_price.png")

    # fig = px.scatter(df, y="price", x="year", color="km_k", facet_col="model", trendline='ols', trendline_color_override="black")
    # fig.update_traces(marker_size=8)
    # fig.update_layout(
    #     title='AutoTraderCa search results on 20/10/2024',
    #     yaxis_title="Price (CAD)"    
    # )
    # fig.update_xaxes(title="Year")
    
    # fig.show()
    # fig.write_image("model_comparison_year_price.png")


    # fig = px.scatter(df, y="mileage_per_yr", x="year", color="model")
    # fig.update_traces(marker_size=8)
    # fig.update_layout(
    #     title='AutoTraderCa search results on 20/10/2024',
    #     yaxis_title="km per year"    
    # )
    # fig.update_xaxes(title="year")
    # fig.show()

    df['year_interaction'] = 2024 - df['year']


    # Fit regression model with interaction term (Make_Model * Year_Age)
    model = ols('price ~ year_interaction * model + km_k', data=df).fit()

    # Output regression results
    print(model.summary())

    with open(f'all_model_w_interaction.txt', 'w') as fh:
            fh.write(model.summary().as_text())


