from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import uuid
from decimal import Decimal, InvalidOperation
from datetime import datetime
from db import initialize_db
from boto3.dynamodb.conditions import Key
import re


dynamodb = initialize_db()
providers_table = dynamodb.Table('Providers')
recharge_plan_table = dynamodb.Table('Recharge_Plans')

def get_provider_id(provider_type, provider_name):
    try:
        response = providers_table.query(
            IndexName='ProviderType-index',
            KeyConditionExpression=Key('ProviderType').eq(provider_type)
        )
        items = response.get('Items', [])
        
        for item in items:
            if item.get('ProviderName') == provider_name:
                provider_id = item['ProviderId']
              
                return provider_id
        
        return None
    except Exception as e:

        return None

def create_plan_item(provider_id, price, plan_details):
    cleaned_price = re.sub(r'[^0-9.]', '', price).strip()
    if not cleaned_price.replace(".", "").isdigit() and cleaned_price != "":
       
        cleaned_price = "N/A" 
    try:
        return {
            "PlanId": str(uuid.uuid4()),
            "ProviderId": provider_id,
            "Price": Decimal(cleaned_price) if cleaned_price != "N/A" else "N/A",
            "PlanDetails": plan_details,
            "createdAt": datetime.now().isoformat()
        }
    except InvalidOperation as e:
        print(f"Invalid price format for plan item: {e}")
    except Exception as e:
        print(f"Error creating plan item: {e}")
    return None
def store_plan_in_dynamodb(plan_item):
    try:
        
        response = recharge_plan_table.put_item(Item=plan_item)
      
    except Exception as e:
        print(f"Error storing plan in DynamoDB: {e}")

def scrape_airtel_plans(provider_id):
    url = 'https://www.airtel.in/recharge-online?icid=header'
    plans = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)

        try:
            page.wait_for_selector("div.packs-card-container", timeout=10000)
        except Exception as e:
           
            return []

        content = page.content()
        soup = BeautifulSoup(content, "html.parser")

        for card in soup.find_all("div", class_="pack-card-container"):
            
            price_element = card.find("h4", class_="pack-card-heading") 
            h6_detail = card.find("h6", class_="pack-card-sub-heading")
            if price_element:
                price = price_element.get_text(strip=True).replace("₹", "").replace(",", "")
               
            else:
                price = "N/A" 

            data_element = card.find_all("div", class_="pack-card-detail")[1]  
            data = data_element.find("h4", class_="pack-card-heading").text.strip() if data_element else "N/A"
            data_info = data_element.find("h6", class_="pack-card-sub-heading").get_text(strip=True) if data_element and data_element.find("h6", class_="pack-card-sub-heading") else ""
            validity_element = card.find_all("div", class_="pack-card-detail")[2] 
            validity = validity_element.find("h4", class_="pack-card-heading").text.strip() if validity_element else "N/A"
            validity_info = validity_element.find("h6", class_="pack-card-sub-heading").get_text(strip=True) if validity_element and validity_element.find("h6", class_="pack-card-sub-heading") else ""
          
            plan_details = f" {data} {data_info} \n {validity} {validity_info}"

          
            additional_benefits = []
            benefits_section = card.find("div", class_="pack-card-benefits")
            if benefits_section:
                benefits = benefits_section.find_all("div", class_="pack-card-benefit")
                for benefit in benefits:
                    benefit_text = benefit.get_text(strip=True)
                    img = benefit.find("img")["src"] if benefit.find("img") else None
                    additional_benefits.append({'text': benefit_text, 'image': img})

            for b in additional_benefits:
                plan_details += f" \n{b['text']}"

            if len(additional_benefits) > 3:
                plan_details += " +3 more"

            
            plan_item = create_plan_item(provider_id, price, plan_details)
            if plan_item:
                plans.append(plan_item)

    return plans


def scrape_bsnl_plans(provider_id):
    url = 'https://www.bsnl.co.in/opencms/bsnl/BSNL/services/mobile/prepaid_plans_100822.html'
    plans = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)

        page.wait_for_selector("div#middle", timeout=10000)
        content = page.content()
        soup = BeautifulSoup(content, "html.parser")

        table_rows = soup.find_all("tr", class_="table_conn")
        if len(table_rows) >=5:
            price_cells = table_rows[0].find_all("td")[1:]
            validity_cells = table_rows[2].find_all("td")[1:]
            data_cells = table_rows[5].find_all("td")[1:]

            for price_cell, validity_cell, data_cell in zip(price_cells, validity_cells, data_cells):
                price_text = price_cell.get_text(strip=True).replace("₹", "").strip()
                validity_text = validity_cell.get_text(strip=True).strip()
                data_text = data_cell.get_text(strip=True).strip()

                plan_details = f"{validity_text}\n {data_text}"
                plan_item = create_plan_item(provider_id, price_text, plan_details)
                if plan_item:
                    plans.append(plan_item)
        else:
            print("Not enough rows with class 'table_conn' to extract BSNL plans.")

        browser.close()

    return plans



def scrape_vodafone_plans(provider_id):
    urls = [
        'https://www.myvi.in/prepaid/best-prepaid-plans',
        'https://www.myvi.in/prepaid/unlimited-calls-and-data-plans'
    ]
    plans = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for url in urls:
            page = browser.new_page()
            page.goto(url)


        try:
            page.wait_for_selector("div.packs", timeout=10000)
        except Exception as e:
           
            return []

        content = page.content()
        soup = BeautifulSoup(content, "html.parser")

       
        for card in soup.find_all("div", class_="cloning-div"):
          
            price_element = card.find("h4", class_="plan-amount")
            price = price_element.get_text(strip=True) if price_element else None

           
            teleco_feature = card.find("div", class_="teleco-feature")
            if teleco_feature:
             
                talktime_element = teleco_feature.find("h4", class_="teleco-benefit talktime")
                talktime = talktime_element.get_text(strip=True) if talktime_element else "No talktime info"

                
                data_element = teleco_feature.find("h4", class_="teleco-benefit data")
                data_label = data_element.find_next_sibling("small").get_text(strip=True) if data_element else ""
                data = f"{data_element.get_text(strip=True)} {data_label}" if data_element else "No data info"

               
                validity_element = teleco_feature.find("h4", class_="teleco-benefit validity")
                validity_label = validity_element.find_next_sibling("small").get_text(strip=True) if validity_element else ""
                validity = f"{validity_element.get_text(strip=True)} {validity_label}" if validity_element else "No validity info"


            
            plan_details = f" {data}\n {validity}\n {talktime} calls"

            
            plan_item = create_plan_item(provider_id, price, plan_details)
            if plan_item:
                plans.append(plan_item)
                browser.close()
                 
    return plans

def scrape_mtnl_plans(provider_id):
    urls = ['https://mtnlmumbai.in/index.php/mobile/3g-prepaid',
    'https://mtnlmumbai.in/index.php/mobile/3g-prepaid/3g-top-up']
    plans = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for url in urls:
            page = browser.new_page()
            page.goto(url)

        try:
            page.wait_for_selector("table#tariff-table", timeout=10000)
        except Exception as e:
         
            browser.close()
            return []

        content = page.content()
        soup = BeautifulSoup(content, "html.parser")
        tables = soup.find_all('table', id='tariff-table')

        for table in tables:
            rows = table.find_all('tr')[1:]  

            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 5:
                    plan_name = cols[0].get_text(strip=True)
                    price = cols[1].get_text(strip=True)
                    data_usage = cols[2].get_text(strip=True)
                    validity = cols[3].get_text(strip=True)
                    sms_benefits = cols[4].get_text(strip=True)
                    
                   
                    voice_benefits = cols[5].get_text(strip=True) if len(cols) > 5 else "N/A"

              
                plan_details = f" {data_usage}\n {validity}\n {sms_benefits}\n {voice_benefits}"
                
                
                plan_item = create_plan_item(provider_id, price, plan_details)
                if plan_item:
                    plans.append(plan_item)

        browser.close()
    return plans


def scrape_jio_plans(provider_id):
    urls = [
        'https://www.jio.com/selfcare/plans/mobility/prepaid-plans-list/',
        'https://www.jio.com/selfcare/plans/mobility/prepaid-plans-list/?category=Data%20Packs&categoryId=RGF0YSBQYWNrcw==',
        'https://www.jio.com/selfcare/plans/mobility/prepaid-plans-list/?category=True%20Unlimited%20Upgrade&categoryId=VHJ1ZSBVbmxpbWl0ZWQgVXBncmFkZQ==',
        'https://www.jio.com/selfcare/plans/mobility/prepaid-plans-list/?category=Entertainment%20Plans&categoryId=RW50ZXJ0YWlubWVudCBQbGFucw==',
        'https://www.jio.com/selfcare/plans/mobility/prepaid-plans-list/?category=Data%20Booster&categoryId=RGF0YSBCb29zdGVy',
        'https://www.jio.com/selfcare/plans/mobility/prepaid-plans-list/?category=Annual%20Plans&categoryId=QW5udWFsIFBsYW5z',
        'https://www.jio.com/selfcare/plans/mobility/prepaid-plans-list/?category=JioBharat%20Phone&categoryId=SmlvQmhhcmF0IFBob25l',
        'https://www.jio.com/selfcare/plans/mobility/prepaid-plans-list/?category=Top-up&categoryId=VG9wLXVw',
        'https://www.jio.com/selfcare/plans/mobility/prepaid-plans-list/?category=JioSaavn%20Pro&categoryId=SmlvU2Fhdm4gUHJv',
        'https://www.jio.com/selfcare/plans/mobility/prepaid-plans-list/?category=Value&categoryId=VmFsdWU=',
        'https://www.jio.com/selfcare/plans/mobility/prepaid-plans-list/?category=Jio%20Phone%20Prima&categoryId=SmlvIFBob25lIFByaW1h',
        'https://www.jio.com/selfcare/plans/mobility/prepaid-plans-list/?category=IR%20Wi-Fi%20Calling&categoryId=SVIgV2ktRmkgQ2FsbGluZw==','https://www.jio.com/selfcare/plans/mobility/prepaid-plans-list/?category=JioPhone%20Data%20Add-on&categoryId=SmlvUGhvbmUgRGF0YSBBZGQtb24=','https://www.jio.com/selfcare/plans/mobility/prepaid-plans-list/?category=ISD&categoryId=SVNE'
    ]
    
    all_plans = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1280, "height": 720})

        for url in urls:
            
            page.goto(url)
            page.wait_for_load_state("networkidle", timeout=60000)

            categories = page.query_selector_all("div.Subcategory_accordion__3ra7i")

            for category in categories:
               
                expand_button = category.query_selector("span.j-accordion-panel-icn")
                if expand_button and "active" not in expand_button.get_attribute("class"):
                    expand_button.click()
                    page.wait_for_timeout(500)

        
                category_name_element = category.query_selector("h1")
                category_name = category_name_element.inner_text() if category_name_element else "Unknown Category"

                plan_elements = category.query_selector_all("div.j-contentBlock")

                for plan_element in plan_elements:
                    try:
                 
                        plan_name_element = plan_element.query_selector("h1.j-text.j-text-heading-xxs")
                        plan_name = plan_name_element.inner_text() if plan_name_element else "N/A"

                        
                        price_element = plan_element.query_selector("div.PlanName_planText__31V3X")
                        price = price_element.inner_text().replace("₹", "").strip() if price_element else "N/A"

                      
                        validity_label_element = plan_element.query_selector("div.ValidityCol_gridItem___UUsq div.j-text-body-xs")
                        validity_value_element = plan_element.query_selector("div.ValidityCol_gridItem___UUsq div.j-text-body-s-bold span")

                        validity_label = validity_label_element.inner_text() if validity_label_element else "N/A"
                        validity_value = validity_value_element.inner_text() if validity_value_element else "N/A"

                        
                        data_label_element = plan_element.query_selector("div.DataCol_gridItem__ZkpDg div.j-text-body-xs")
                        data_value_element = plan_element.query_selector("div.DataCol_gridItem__ZkpDg span.DataCol_font__1BS2q")

                        data_label = data_label_element.inner_text() if data_label_element else "N/A"
                        data_value = data_value_element.inner_text() if data_value_element else "N/A"

                        subscriptions = []
                        subscription_elements = plan_element.query_selector_all("div.Subscriptions_mainCont__2Vp-t img.Subscriptions_img__6ZCDs")
                        for subscription in subscription_elements:
                            img_url = subscription.get_attribute("src")
                            if img_url:
                                subscriptions.append(img_url)

                        additional_subscriptions_element = plan_element.query_selector("div.Subscriptions_mainCont__2Vp-t div.j-text-body-xs")
                        additional_text = additional_subscriptions_element.inner_text() if additional_subscriptions_element else ""
                        if additional_text:
                            subscriptions.append(additional_text.strip())

                        plan_details = f"{data_label}  {data_value}\n {validity_label} {validity_value}\n {category_name}\n{', '.join(subscriptions)}"

                        plan_item = create_plan_item(provider_id, price, plan_details)
                        if plan_item:
                         all_plans.append(plan_item)

                    except Exception as e:
                       
                        continue

        browser.close()

    return all_plans
def scrape_and_store_all_plans():
    providers = [
        {"provider_type": "Mobile", "provider_name": "Airtel"},
        {"provider_type": "Mobile", "provider_name": "Jio"},
        {"provider_type": "Mobile", "provider_name": "BSNL"},
        {"provider_type": "Mobile", "provider_name": "VodafoneIndia"},
        {"provider_type": "Mobile", "provider_name": "MTNL"},
        
    ]

    for provider in providers:
        provider_type = provider["provider_type"]
        provider_name = provider["provider_name"]
        
        provider_id = get_provider_id(provider_type, provider_name)
        if not provider_id:
          
            continue

        if provider_name == "Airtel":
            plans = scrape_airtel_plans(provider_id)
        elif provider_name == "MTNL":
            plans = scrape_mtnl_plans(provider_id)
        elif provider_name == "BSNL":
            plans = scrape_bsnl_plans(provider_id)
        elif provider_name == "VodafoneIndia":  
            plans = scrape_vodafone_plans(provider_id)
        elif provider_name == "Jio":
            plans = scrape_jio_plans(provider_id)
        plan_count = len(plans)
       

        for plan in plans:
            store_plan_in_dynamodb(plan)
