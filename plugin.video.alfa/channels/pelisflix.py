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

from channels import autoplay
from platformcode import config, logger, platformtools
from core.item import Item
from core import httptools, scrapertools, jsontools, tmdb
from core import servertools, channeltools
from channels import filtertools
from bs4 import BeautifulSoup
from channelselector import get_thumb

SERVER = {'Ok': 'okru','Flixplayer': 'gounlimited', 'gounlimited': 'gounlimited', 'VIP': 'VIP', 'Dood': 'Doodstream', 'Femax20': 'Fembed' }
IDIOMAS = {"Spain": "CAST", "Mexico": "LAT", "United-States-of-AmericaUSA": "VOSE", "Castellano": "CAST", "Latino": "LAT", "Subtitulado": "VOSE"}
list_language = list(IDIOMAS.values())
list_quality = []
list_servers = list(SERVER.values())

canonical = {
             'channel': 'pelisflix', 
             'host': config.get_setting("current_host", 'pelisflix', default=''), 
             'host_alt': ["https://pelisflix.li/"], 
             'host_black_list': [], 
             'CF': False, 'CF_test': False, 'alfa_s': True
            }
host = canonical['host'] or canonical['host_alt'][0]
host_save = host
__channel__ = canonical['channel']


def mainlist(item):
    logger.info()
    itemlist = []
    autoplay.init(item.channel, list_servers, list_quality)
    
    itemlist.append(item.clone(title="Peliculas" , action="lista", url= host + "ver-peliculas-online-gratis/", thumbnail=get_thumb("movies", auto=True)))
    itemlist.append(item.clone(title="Genero" , action="categorias", url= host, thumbnail=get_thumb('genres', auto=True)))
    itemlist.append(item.clone(title="Series", action="lista", url= host + "ver-series-online-gratis/", thumbnail=get_thumb("tvshows", auto=True)))
    # itemlist.append(item.clone(title="Anime", action="lista", url= host + "category/anime/", thumbnail=get_thumb("anime", auto=True)))

    itemlist.append(item.clone(title="Productora" , action="categorias", url= host))
    itemlist.append(item.clone(title="Año" , action="anno"))
    # itemlist.append(item.clone(title="Alfabetico", action="section", url=host, thumbnail=get_thumb("alphabet", auto=True)))
    itemlist.append(item.clone(title="Buscar...", action="search", thumbnail=get_thumb("search", auto=True)))

    autoplay.show_option(item.channel, itemlist)
    return itemlist


def configuracion(item):
    from platformcode import platformtools
    ret = platformtools.show_channel_settings()
    platformtools.itemlist_refresh()
    return ret


def search(item, texto):
    logger.info()
    try:
        texto = texto.replace(" ", "+")
        item.url = "%s?s=%s" % (host, texto)
        if texto != "":
            return lista(item)
        else:
            return []
    # Se captura la excepción, para no interrumpir al buscador global si un canal falla
    except:
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []


def anno(item):
    logger.info()
    itemlist = []
    from datetime import datetime
    now = datetime.now()
    year = int(now.year)
    while year >= 1940:
        itemlist.append(item.clone(title="%s" %year, action="lista", url= "%srelease/%s" % (host,year)))
        year -= 1
    return itemlist


def categorias(item):
    logger.info()
    itemlist = []
    if "Genero" in item.title:
        soup = create_soup(item.url).find("li", id="menu-item-11043").parent
    else:
        soup = create_soup(item.url).find("li", id="menu-item-109").parent
    matches = soup.find_all("li")
    for elem in matches:
        url = elem.a["href"]
        title = elem.a.text
        itemlist.append(item.clone(action="lista", url=url, title=title))
    if "Genero" in item.title:
        itemlist.append(item.clone(action="lista", url="%scategory/dc-comics/" %host, title="DC"))
        itemlist.append(item.clone(action="lista", url="%scategory/marvel/" %host, title="MARVEL"))
    return itemlist


def section(item):
    logger.info()
    itemlist = []
    soup = create_soup(item.url).find("ul", class_="AZList")
    for elem in soup.find_all("li"):
        url = elem.a["href"]
        title = elem.a.text
        itemlist.append(item.clone(action="alpha_list", url=url, title=title))
    return itemlist


def alpha_list(item):
    logger.info()
    itemlist = []
    soup = create_soup(item.url)
    matches = soup.find("tbody")
    if not matches:
        return itemlist
    for elem in matches.find_all("tr"):
        info = elem.find("td", class_="MvTbTtl")
        thumbnail = elem.img["data-lazy-src"]
        url = info.a["href"]
        title = info.a.text.strip()
        year = elem.find_all('td')[4].text
        new_item = item.clone(url=url, title=title, thumbnail=thumbnail, infoLabels={"year": year})
        if "series" in url:
            new_item.action = "seasons"
            new_item.contentSerieName = title
        else:
            new_item.action = "findvideos"
            new_item.contentTitle = title
            # new_item.language = language
        itemlist.append(new_item)

    tmdb.set_infoLabels_itemlist(itemlist, True)

    if not config.get_setting('unify') and not channeltools.get_channel_parameters(__channel__)['force_unify']:
        a = len(itemlist)-1
        for i in itemlist:
            if a >= 0:
                title= itemlist[a].contentTitle
                titulo = itemlist[a].title
                titulo = scrapertools.find_single_match(titulo, '(\\[COLOR[^"]+)')
                title = "%s %s" %(title, titulo)
                itemlist[a].title = title
                a -= 1
    next_page = soup.find('a', class_='current')
    if next_page and next_page.find_next_sibling("a"):
        next_page = next_page.find_next_sibling("a")['href']
        next_page = urlparse.urljoin(item.url,next_page)
        itemlist.append(item.clone(action="alpha_list", title="[COLOR blue]Página Siguiente >>[/COLOR]", url=next_page) )
    return itemlist


def create_soup(url, referer=None, post=None, unescape=False):
    logger.info()
    if referer:
        data = httptools.downloadpage(url, headers={'Referer': referer}, canonical=canonical).data
    elif post:
        data = httptools.downloadpage(url, post=post, canonical=canonical).data
    else:
        data = httptools.downloadpage(url, canonical=canonical).data
    if unescape:
        data = scrapertools.unescape(data)
    soup = BeautifulSoup(data, "html5lib", from_encoding="utf-8")
    return soup


def lista(item):
    logger.info()
    itemlist = []
    soup = create_soup(item.url, referer=host)
    matches = soup.find_all("li", id=re.compile(r"^post-\d+"))
    for elem in matches:
        url = elem.a['href']
        thumbnail = elem.figure.img['data-src']
        lg = elem.find(class_='Lg')
        if lg:
            lg = lg.find_all('img')
            language = []
            for l in lg:
                if l.has_attr('data-lazy-src'):
                    lang = l['data-lazy-src']
                else:
                    lang = l['src']
                lang = scrapertools.find_single_match(lang,'/([A-z-]+).png')
                language.append(IDIOMAS.get(lang, lang))
        year = elem.find(class_='Date')
        if year:
            year = year.text
        else:
            year = elem.find(class_='Date')
        title = elem.h2.text.strip()
        if year == '':
            year = '-'
        new_item = item.clone(url=url, title=title, thumbnail=thumbnail, infoLabels={"year": year})
        if "serie" in url:
            new_item.action = "seasons"
            new_item.contentSerieName = title
        else:
            new_item.action = "findvideos"
            new_item.contentTitle = title
            new_item.language = language
        itemlist.append(new_item)

    tmdb.set_infoLabels(itemlist, True)

    if not config.get_setting('unify') and not channeltools.get_channel_parameters(__channel__)['force_unify']:
        a = len(itemlist)-1
        for i in itemlist:
            if a >= 0:
                title= itemlist[a].contentTitle
                titulo = itemlist[a].title
                titulo = scrapertools.find_single_match(titulo, '(\\[COLOR[^"]+)')
                title = "%s %s" %(title, titulo)
                itemlist[a].title = title
                a -= 1
    next_page = soup.find('a', class_='current')
    if next_page and next_page.find_next_sibling("a"):
        next_page = next_page.find_next_sibling("a")['href']
        next_page = urlparse.urljoin(item.url,next_page)
        itemlist.append(item.clone(action="lista", title="[COLOR blue]Página Siguiente >>[/COLOR]", url=next_page) )
    return itemlist


def seasons(item):
    logger.info()
    itemlist = list()
    soup = create_soup(item.url)
    matches = soup.find_all("section", class_="SeasonBx")
    infoLabels = item.infoLabels
    for elem in matches:
        url = elem.a['href']
        season = elem.find("span").text
        title = "Temporada %s" % season
        infoLabels["season"] = season
        itemlist.append(item.clone(title=title, url=url, action="episodesxseasons", infoLabels=infoLabels))
    tmdb.set_infoLabels_itemlist(itemlist, True)
    if config.get_videolibrary_support() and len(itemlist) > 0:
        itemlist.append(item.clone(title="[COLOR yellow]Añadir esta serie a la videoteca[/COLOR]", url=item.url,
                        action="add_serie_to_library", extra="episodios", contentSerieName=item.contentSerieName))
    return itemlist


def episodesxseasons(item):
    logger.info()
    itemlist = list()
    soup = create_soup(item.url)
    matches = soup.find_all("tr", class_="Viewed")
    infoLabels = item.infoLabels
    season = infoLabels["season"]
    for elem in matches:
        url = elem.a["href"]
        epi = elem.find('span', class_='Num').text
        infoLabels["episode"] = epi
        title = "%sx%s - Episodio %s" % (season, epi, epi)
        itemlist.append(item.clone(title=title, url=url, action="findvideos", infoLabels=infoLabels))
    tmdb.set_infoLabels_itemlist(itemlist, True)
    return itemlist


def episodios(item):
    logger.info()
    itemlist = []
    templist = seasons(item)
    for tempitem in templist:
        itemlist += episodesxseasons(tempitem)
    return itemlist


def findvideos(item):
    logger.info()
    itemlist = []
    soup = create_soup(item.url)
    matches = soup.find_all('button', class_='sgty')
    serv=[]
    for elem in matches:
        num= elem['data-key']
        id= elem['data-id']
        type = elem['data-typ']
        if "movie" in type: type = "1"
        else: type = "2"
        prop = elem.find_all('span')[1].text.split()
        lang= prop[0]
        server = prop[-1]
        lang = IDIOMAS.get(lang, lang)
        url = "%s?trembed=%s&trid=%s&trtype=%s"  %  (host,num,id, type)
        server = SERVER.get(server, server)

        if not config.get_setting('unify') and not channeltools.get_channel_parameters(__channel__)['force_unify']:
            title = "[%s] [COLOR darkgrey][%s][/COLOR]" %(server,lang)
        else:
            title = server
        if not "gounlimited" in server:
            itemlist.append(item.clone(action="play", title=title, url=url, server=server, language=lang ))
        if "VIP" in server:
            url = create_soup(url).find(class_='Video').iframe['src']
            data = httptools.downloadpage(url).data
            matches = re.compile("go_to_player\('([^']+)'\)", re.DOTALL).findall(data)
            for url in matches:
                itemlist.append(Item(channel=item.channel, title="%s", url=url, action="play", language=lang))

            itemlist = servertools.get_servers_itemlist(itemlist, lambda i: i.title % i.server)

    itemlist.sort(key=lambda it: (it.language))

    # Requerido para FilterTools
    itemlist = filtertools.get_links(itemlist, item, list_language)
    # Requerido para AutoPlay
    autoplay.start(itemlist, item)

    if config.get_videolibrary_support() and len(itemlist) > 0 and item.extra !='findvideos' and not "/episodios/" in item.url :
        itemlist.append(item.clone(action="add_pelicula_to_library", 
                             title='[COLOR yellow]Añadir esta pelicula a la videoteca[/COLOR]', url=item.url,
                             extra="findvideos", contentTitle=item.contentTitle)) 
    return itemlist


def play(item):
    logger.info()
    itemlist = []
    logger.debug("ITEM: %s" % item)
    if "pelisflix" in item.url:
        url = create_soup(item.url).find(class_='Video').iframe['src']
        id = scrapertools.find_single_match(url, r"\?h=([A-z0-9]+)")
        post_url= "%sstream/r.php" % host
        post = {'h' : id}
        url = httptools.downloadpage(post_url, post=post, follow_redirects=False).headers['location']
    else:
        url = item.url
    if "byegoto" in url:
        id = scrapertools.find_single_match(url, '=([^"]+)')
        url = "%sbyegoto/rd.php" % host
        post = {'url': id}
        url = httptools.downloadpage(url, post=post).url
    if "mega1080p" in url:
        from lib import jsunpack
        url = httptools.downloadpage(url).data
        pack = scrapertools.find_single_match(url, "p,a,c,k,e,d.*?</script>")
        unpack = jsunpack.unpack(pack).replace("\\", "")
        url = scrapertools.find_single_match(unpack, "'file':'([^']+)'")
        url = url.replace("/master", "/720/720p")
        url = "https://pro.mega1080p.club/%s" %url
        url += "|Referer=%s" %url
        
    itemlist.append(item.clone(action="play", title= "%s", contentTitle = item.title, url=url))
    itemlist = servertools.get_servers_itemlist(itemlist, lambda i: i.title % i.server.capitalize())
    return itemlist

