import aiohttp
import asyncio
from bs4 import BeautifulSoup
import os


async def find(request):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://www.myinstants.com/ru/search/?name=" + request
        ) as response:
            if response.status == 200:
                soup = BeautifulSoup(await response.text(), "html.parser")
                results = []
                for instant in soup.select(".instant"):
                    # Извлекаем название
                    name_link = instant.select_one(".instant-link")
                    if not name_link:
                        continue
                    name = name_link.text.strip()

                    # Извлекаем путь к MP3 из кнопки
                    button = instant.select_one('button[onclick^="play("]')
                    if not button:
                        continue

                    onclick_attr = button.get("onclick", "")
                    start = onclick_attr.find("'") + 1
                    end = onclick_attr.find("'", start)
                    mp3_path = onclick_attr[start:end]

                    if mp3_path.endswith(".mp3"):
                        results.append((name, mp3_path))

                return results

            else:
                print(f"Ошибка запроса: {response.status}")
                return None


async def download_file(session, url, save_path):
    try:
        async with session.get(url) as response:
            if response.status == 200:
                with open(save_path, "wb") as f:
                    while True:
                        chunk = await response.content.read(1024)
                        if not chunk:
                            break
                        f.write(chunk)
                return True
            else:
                print(f"❌ Ошибка {response.status}: Не удалось скачать {url}")
                return False
    except Exception as e:
        print(f"❌ Ошибка при загрузке {url}: {e}")
        return False


async def get_popular(page=1):
    base_url = "https://www.myinstants.com"
    download_folder = "myinstants_sounds"
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://www.myinstants.com/en/index/ru/?page=" + str(page)
        ) as response:
            if response.status == 200:

                soup = BeautifulSoup(await response.text(), "html.parser")
                sound_elements = soup.select("div.instant")
                results = []
                for element in sound_elements:
                    name = element.select_one("a.instant-link").text.strip()
                    button = element.select_one("button.small-button")
                    onclick_attr = button.get("onclick", "")
                    start = onclick_attr.find("'") + 1
                    end = onclick_attr.find("'", start)
                    mp3_path = onclick_attr[start:end]
                    if mp3_path.endswith(".mp3"):
                        results.append(
                            {
                                "name": name,
                                "path": "myinstants_sounds/" + mp3_path.split("/")[-1],
                            }
                        )
                        if mp3_path.split("/")[-1] not in os.listdir(download_folder):
                            filename = os.path.join(
                                download_folder, mp3_path.split("/")[-1]
                            )
                            res = await download_file(
                                session, base_url + mp3_path, filename
                            )

                return results


async def main(request):
    base_url = "https://www.myinstants.com"
    search_url = request
    download_folder = "myinstants_sounds"
    os.makedirs(download_folder, exist_ok=True)

    # Парсим страницу и получаем ссылки на MP3
    mp3_urls = await find(search_url)
    if not mp3_urls:
        print("Не найдено MP3-файлов.")
        return
    async with aiohttp.ClientSession() as session:
        tasks = []
        for name, url in mp3_urls:
            if url.split("/")[-1] not in os.listdir(download_folder):
                filename = os.path.join(download_folder, url.split("/")[-1])
                tasks.append(download_file(session, base_url + url, filename))
        results = await asyncio.gather(*tasks)
        res = [
            {"name": name, "path": download_folder + "/" + url.split("/")[-1]}
            for name, url in mp3_urls
        ]
        return res
