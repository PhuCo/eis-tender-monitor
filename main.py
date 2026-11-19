import asyncio
import re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from database import add_tender

async def parse_eis_tenders(pages_to_parse: int = 3):   #collects lots from the specified number of pages
# ETL model for collecting tenders from the Unified Information System and returns a list of cleaned dictionaries with lot data

    print(f"запуск парсера, выдано страниц : {pages_to_parse}")
    results_list=[]

    async with async_playwright() as p: #starting Chrome work
        browser = await p.chromium.launch(
            headless=True,
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        )

        context = await browser.new_context(
            ignore_https_errors = True, #bypass the missing certificate error in Chrome
            viewport = {"width":1920, "height":1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36" #
        )

        page = await context.new_page()
        await page.add_init_script("delete navigator.__proto__.webdriver;")
        print("переход на страницу тендеров")
        await page.goto("https://zakupki.gov.ru/epz/order/extendedsearch/results.html", wait_until="networkidle", timeout = 60000)

        for current_page in range(1,6):
            print(f"Сканирую страницу {current_page} на сайте ЕИС")
            await asyncio.sleep(1.5)
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
            tenders = soup.find_all("div", class_="search-registry-entry-block")

            for tender in tenders:
                tender_id = "not found" #collecting a number using regular expressions
                all_links = tender.find_all("a")

                for link in all_links:
                    link_text = link.get_text(strip=True). replace("№", "").strip()
                    if re.match(r"^\d+$", link_text) and len(link_text) in [11,19]:
                        tender_id = link_text
                        break

            #customer name
                customer_tag = tender.find("div", class_="registry-entry__body-href") or \
                                tender.find("a", class_="registry-entry__body-href") or \
                                tender.find("div", class_="registry-entry__body-title")
                customer = "not found"
                if customer_tag:
                    raw_text = customer_tag.get_text(separator=" ", strip=True)
                    customer= " ".join(raw_text.split())

            #price НМЦК
                price_tag = tender.find("div", class_="price-block__value") or \
                            tender.find("span", class_="price-block__value")
                price = price_tag.get_text(strip=True) if price_tag else "0"

                results_list.append({
                    "id": tender_id,
                    "customer": customer,
                    "price": price
                })
            if current_page<5:
                try:
                    next_button = page.locator("a.page-html.next")
                    if await next_button.is_visible():
                        await next_button.click()
                        await page.wait_for_load_state("networkidle")
                    else:
                        print("Кнопка 'Далее' не найдена. Достигнут конец выдачи сайта.")
                        break
                except Exception as e:
                    print(f"Ошибка при переходе на следующую страницу: {str(e)}")
                    break
        await context.close()
        await browser.close()

    print(f"Сбор завершен, всего файлов: {len(results_list)}")
    return results_list
        
async def main():
    data = await parse_eis_tenders()

    print("\n синхронизация с локальной базой данных")
    new_counter = 0
    duplicate_counter = 0

    for item in data:
        is_saved = add_tender(item["id"], item["customer"], item["price"])

        if is_saved:
            print(f"Новый лот успешно загружен в базу: {item['id']}")
            new_counter += 1
        else:
            print(f"Дубликат пропущен базой: {item['id']}")
            duplicate_counter += 1

    print(f"\n  Итоги снхронизации: Записано новых лотов: {new_counter} | Пропущено дубликатов: {duplicate_counter}")

if __name__=="__main__":
    asyncio.run(main())