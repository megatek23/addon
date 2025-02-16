# -*- coding: utf-8 -*-
#------------------------------------------------------------
import sys
PY3 = False
if sys.version_info[0] >= 3: PY3 = True; unicode = str; unichr = chr; long = int

if PY3:
    import urllib.parse as urlparse                             # Es muy lento en PY2.  En PY3 es nativo
else:
    import urlparse                                             # Usamos el nativo de PY2 que es más rápido

import re

from platformcode import config, logger
from core import httptools, scrapertools, tmdb
from core import servertools
from core.item import Item
from channels import filtertools
from channels import autoplay
from bs4 import BeautifulSoup

IDIOMAS = {'vo': 'VO'}
list_language = list(IDIOMAS.values())
list_quality = []
list_servers = ['mangovideo']

host = 'https://xxxparodyhd.net'   #  https://pandamovies.pw  'https://watchpornfree.info'   'https://xxxparodyhd.net'  
                                   #  https://www.netflixporno.net  https://xxxscenes.net  playpornx

def mainlist(item):
    logger.info()
    itemlist = []

    autoplay.init(item.channel, list_servers, list_quality)

    itemlist.append(item.clone(title="Nuevas" , action="lista", url=host + "/movies/"))
    itemlist.append(item.clone(title="Mas Vistas" , action="lista", url=host + "/most-viewed/"))
    itemlist.append(item.clone(title="Mejor Valoradas" , action="lista", url=host + "/most-rating/"))
    itemlist.append(item.clone(title="Año" , action="categorias", url=host))
    itemlist.append(item.clone(title="Canal" , action="categorias", url=host))
    itemlist.append(item.clone(title="Categorias" , action="categorias", url=host))
    itemlist.append(item.clone(title="Buscar", action="search"))

    autoplay.show_option(item.channel, itemlist)

    return itemlist


def search(item, texto):
    logger.info()
    texto = texto.replace(" ", "+")
    item.url = "%s/search/%s" % (host,texto)
    try:
        return lista(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []


def categorias(item):
    logger.info()
    itemlist = []
    soup = create_soup(item.url).find('ul', class_='top-menu')
    if "Categorias" in item.title:
        matches = soup.find_all(href=re.compile("/genre/"))
    elif "Year" in item.title:
        matches = soup.find_all(href=re.compile("/release-year/"))
    else:
        matches = soup.find_all(href=re.compile("/director/"))
    for elem in matches:
        url = elem['href']
        title = elem.text.strip()
        plot = ""
        thumbnail = ""
        if not url.startswith("https"):
            url = "https:%s" % url
        itemlist.append(item.clone(action="lista", title=title, url=url,
                             thumbnail=thumbnail, plot=plot))
    if "Year" in item.title:
        itemlist.reverse()
    return itemlist


def create_soup(url, referer=None, unescape=False):
    logger.info()
    if referer:
        data = httptools.downloadpage(url, headers={'Referer': referer}).data
    else:
        data = httptools.downloadpage(url).data
    if unescape:
        data = scrapertools.unescape(data)
    soup = BeautifulSoup(data, "html5lib", from_encoding="utf-8")
    return soup


def lista(item):
    logger.info()
    itemlist = []
    soup = create_soup(item.url)
    matches = soup.find_all('div', class_='ml-item')
    for elem in matches:
        url = elem.a['href']
        title = elem.a['oldtitle']
        thumbnail = elem.img['src']
        if not "xxxscenes" in item.url:
            year = elem.find('div', class_='jtip-top').a.text.strip()
        else:
            year = ""
        itemlist.append(item.clone(action="findvideos", title=title, url=url, thumbnail=thumbnail,
                             fanart=thumbnail, contentTitle=title, infoLabels={"year": year} ))
    next_page = soup.find('li', class_='active')
    if next_page and next_page.find_next_sibling("li"):
        next_page = next_page.find_next_sibling("li").a['href']
        next_page = urlparse.urljoin(item.url, next_page)
        itemlist.append(item.clone(action="lista", title="[COLOR blue]Página Siguiente >>[/COLOR]", url=next_page) )
    return itemlist


def findvideos(item):
    logger.info()
    itemlist = []
    video_urls = []
    soup = create_soup(item.url).find('div', id='pettabs')
    matches = soup.find_all('a')
    for elem in matches:
        url = elem['href']
        if not url in video_urls:
            video_urls += url
            itemlist.append(item.clone(title='%s', url=url, action='play', language='VO',contentTitle = item.contentTitle))
    itemlist = servertools.get_servers_itemlist(itemlist, lambda x: x.title % x.server)
    # Requerido para FilterTools
    itemlist = filtertools.get_links(itemlist, item, list_language, list_quality)
    # Requerido para AutoPlay
    autoplay.start(itemlist, item)
    return itemlist

