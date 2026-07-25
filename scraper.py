"""
VAgent Web Scraper - Large-scale direct HTTP web research engine.

Scrapes 1,000+ trending sources across 15+ categories using RSS feeds and
HTML parsing. Designed for concurrent multi-agent research at scale.
"""

import asyncio
import hashlib
import json
import logging
import random
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Any, Set, Tuple
from urllib.parse import urlparse, urljoin

import httpx
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

# ─── Rate Limiter ─────────────────────────────────────────────────────────

class DomainRateLimiter:
    """Per-domain rate limiter with exponential backoff."""

    def __init__(self, min_interval: float = 1.0, max_backoff: float = 60.0):
        self._last_access: Dict[str, float] = {}
        self._backoff: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, url: str):
        """Wait until it's safe to fetch from the domain."""
        domain = urlparse(url).netloc
        async with self._lock:
            now = time.monotonic()
            wait = self._backoff.get(domain, 0.0)
            last = self._last_access.get(domain, 0.0)
            since_last = now - last
            needed = max(0.0, wait - since_last)
            if needed > 0:
                await asyncio.sleep(needed)
            self._last_access[domain] = now

    def report_failure(self, url: str):
        """Report a failure, increasing backoff for the domain."""
        domain = urlparse(url).netloc
        current = self._backoff.get(domain, 1.0)
        self._backoff[domain] = min(current * 2, 60.0)

    def report_success(self, url: str):
        """Report a success, gradually decreasing backoff."""
        domain = urlparse(url).netloc
        current = self._backoff.get(domain, 0.0)
        if current > 0:
            self._backoff[domain] = max(0.0, current * 0.5)

# ─── Trending Sources (1,000+) ────────────────────────────────────────────

def _build_trending_sources() -> Dict[str, List[Dict]]:
    """Build the master source list (1,000+ entries)."""
    s: Dict[str, List[Dict]] = defaultdict(list)

    def add(category: str, url: str, stype: str = 'rss', selector: str = ''):
        entry: Dict[str, Any] = {'url': url, 'type': stype}
        if stype == 'html' and selector:
            entry['selector'] = selector
        s[category].append(entry)

    # ════════════════════════════════════════════════════════════════
    # TECHNOLOGY (~200 sources)
    # ════════════════════════════════════════════════════════════════
    t = 'technology'
    # Major tech news
    for url in [
        'https://news.ycombinator.com/', 'https://www.theverge.com/tech',
        'https://arstechnica.com/', 'https://techcrunch.com/',
        'https://www.wired.com/', 'https://www.cnet.com/',
        'https://www.zdnet.com/', 'https://www.engadget.com/',
        'https://gizmodo.com/', 'https://www.anandtech.com/',
        'https://www.tomshardware.com/', 'https://www.digitaltrends.com/',
        'https://thenextweb.com/', 'https://www.techradar.com/',
        'https://venturebeat.com/', 'https://www.fastcompany.com/technology',
        'https://www.pcmag.com/', 'https://www.laptopmag.com/',
        'https://www.computerworld.com/', 'https://www.infoworld.com/',
        'https://www.networkworld.com/', 'https://www.itworld.com/',
        'https://www.csoonline.com/', 'https://www.techrepublic.com/',
    ]:
        add(t, url, 'html', 'h2 a, h3 a, .title a, .headline a, article a')
    # Dev/engineering
    for url in [
        'https://github.com/trending', 'https://stackoverflow.blog/',
        'https://dev.to/', 'https://medium.com/tag/technology',
        'https://hackernoon.com/', 'https://www.freecodecamp.org/news/',
        'https://css-tricks.com/', 'https://www.smashingmagazine.com/',
        'https://www.sitepoint.com/', 'https://www.toptal.com/blog',
        'https://blog.google/technology/', 'https://engineering.fb.com/',
        'https://engineering.linkedin.com/blog', 'https://netflixtechblog.com/',
        'https://blog.twitter.com/engineering', 'https://slack.engineering/',
        'https://engineering.atspotify.com/', 'https://blog.uber.com/engineering',
        'https://developers.facebook.com/blog/', 'https://developer.apple.com/news/',
        'https://android-developers.googleblog.com/', 'https://blogs.windows.com/windowsdeveloper/',
    ]:
        add(t, url, 'html', 'h2 a, h3 a, .post-title a, .entry-title a')
    # Tech RSS
    for url in [
        'https://hnrss.org/frontpage', 'https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml',
        'https://feeds.feedburner.com/TechCrunch/', 'https://www.theverge.com/rss/index.xml',
        'https://feeds.arstechnica.com/arstechnica/index', 'https://www.wired.com/feed/rss',
        'https://www.cnet.com/rss/news/', 'https://www.zdnet.com/news/rss.xml',
        'https://www.engadget.com/rss.xml', 'https://gizmodo.com/rss',
        'https://feeds.feedburner.com/TechRepublic', 'https://venturebeat.com/feed/',
        'https://thenextweb.com/feed/', 'https://www.techradar.com/rss',
        'https://www.digitaltrends.com/feed/', 'https://feeds.feedburner.com/Tomshardware',
        'https://www.anandtech.com/rss/', 'https://news.ycombinator.com/rss',
        'https://hnrss.org/newest?q=AI+OR+LLM+OR+GPT+OR+transformer+OR+database',
        'https://stackoverflow.blog/feed/', 'https://dev.to/feed',
        'https://blog.google/technology/feed/', 'https://engineering.fb.com/feed/',
        'https://netflixtechblog.com/feed', 'https://slack.engineering/feed.xml',
        'https://engineering.atspotify.com/feed.xml',
    ]:
        add(t, url, 'rss')
    # Regional tech
    for url in [
        'https://technode.com/', 'https://www.scmp.com/tech',
        'https://www.theregister.com/', 'https://www.channelnewsasia.com/topic/technology',
        'https://www.afr.com/technology', 'https://www.smh.com.au/technology',
        'https://economictimes.indiatimes.com/tech', 'https://tech.hindustantimes.com/',
        'https://www.businesstoday.in/technology', 'https://gadgets360.com/',
        'https://www.techinasia.com/', 'https://e27.co/',
        'https://www.digit.in/', 'https://www.techworm.net/',
    ]:
        add(t, url, 'html', 'h2 a, h3 a, .title a, article a')
    # Tech RSS regional
    for url in [
        'https://technode.com/feed/', 'https://www.theregister.com/headlines.rss',
        'https://www.afr.com/technology/rss', 'https://gadgets360.com/rss/feeds',
        'https://www.techinasia.com/feed', 'https://e27.co/feed/',
    ]:
        add(t, url, 'rss')
    # Tech company blogs
    for url in [
        'https://www.apple.com/newsroom/', 'https://blog.google/',
        'https://blogs.microsoft.com/blog/', 'https://www.amazon.science/blog',
        'https://blog.twitter.com/', 'https://about.fb.com/news/',
        'https://newsroom.tiktok.com/', 'https://blog.snap.com/',
        'https://www.uber.com/blog/', 'https://www.airbnb.com/resources',
        'https://blog.dropbox.com/', 'https://blog.box.com/',
        'https://www.notion.so/blog', 'https://slack.com/blog',
        'https://blog.atlassian.com/', 'https://circleci.com/blog/',
        'https://github.blog/', 'https://about.gitlab.com/blog/',
        'https://blog.docker.com/', 'https://kubernetes.io/blog/',
        'https://www.hashicorp.com/blog', 'https://www.datadoghq.com/blog/',
        'https://www.mongodb.com/blog', 'https://redis.com/blog/',
        'https://www.postgresql.org/about/news/', 'https://www.mysql.com/news/',
        'https://cloud.google.com/blog/', 'https://aws.amazon.com/blogs/',
        'https://azure.microsoft.com/blog/', 'https://www.digitalocean.com/blog',
        'https://www.linode.com/blog/', 'https://www.vultr.com/news/',
        'https://blog.cloudflare.com/', 'https://www.fastly.com/blog/',
        'https://www.nginx.com/blog/', 'https://blog.traefik.io/',
        'https://www.twilio.com/blog', 'https://www.sendgrid.com/blog/',
        'https://www.stripe.com/blog', 'https://www.paypal.com/stories',
        'https://squareup.com/us/en/townsquare',
    ]:
        add(t, url, 'html', 'h2 a, h3 a, .post-title a, .entry-title a, article a')

    # ════════════════════════════════════════════════════════════════
    # AI (~120 sources)
    # ════════════════════════════════════════════════════════════════
    a = 'ai'
    for url in [
        'https://www.artificialintelligence-news.com/',
        'https://news.mit.edu/topic/artificial-intelligence2',
        'https://www.deeplearning.ai/the-batch/', 'https://www.assemblyai.com/blog/',
        'https://openai.com/blog', 'https://www.anthropic.com/blog',
        'https://blog.google/technology/ai/', 'https://ai.meta.com/blog/',
        'https://deepmind.google/blog/', 'https://blogs.microsoft.com/ai/',
        'https://research.ibm.com/blog', 'https://aws.amazon.com/blogs/machine-learning/',
        'https://blogs.nvidia.com/', 'https://intel.com/content/www/us/en/newsroom/home.html',
        'https://spectrum.ieee.org/topic/artificial-intelligence/',
        'https://www.technologyreview.com/topic/artificial-intelligence/',
        'https://www.marktechpost.com/', 'https://syncedreview.com/',
        'https://www.johnscra.com/', 'https://www.unite.ai/',
        'https://www.machinelearningmastery.com/blog/',
        'https://towardsdatascience.com/', 'https://www.analyticsvidhya.com/blog/',
        'https://www.kdnuggets.com/', 'https://www.datasciencecentral.com/',
        'https://www.oreilly.com/radar/topics/ai/', 'https://lambdalabs.com/blog',
        'https://huggingface.co/blog', 'https://www.fast.ai/',
        'https://jalammar.github.io/', 'https://lena-voita.github.io/',
        'https://ai.googleblog.com/', 'https://research.google/blog/',
        'https://ai.meta.com/blog/', 'https://www.microsoft.com/en-us/research/topic/artificial-intelligence/',
        'https://baai.ac.cn/', 'https://www.deepseek.com/',
        'https://mistral.ai/news/', 'https://cohere.com/blog',
        'https://www.databricks.com/blog/category/ai', 'https://scale.com/blog',
        'https://www.runwayml.com/blog/', 'https://stability.ai/blog',
        'https://replicate.com/blog', 'https://together.ai/blog',
    ]:
        add(a, url, 'html', 'h2 a, h3 a, .post-title a, .entry-title a')
    for url in [
        'https://rss.nytimes.com/services/xml/rss/nyt/ArtificialIntelligence.xml',
        'https://hnrss.org/newest?q=%22artificial+intelligence%22+OR+%22machine+learning%22+OR+%22deep+learning%22+OR+LLM+OR+%22large+language+model%22+OR+GPT+OR+generative',
        'https://www.technologyreview.com/topic/artificial-intelligence/feed/',
        'https://openai.com/blog/feed.xml', 'https://www.anthropic.com/feed.xml',
        'https://ai.meta.com/blog/feed/', 'https://blog.google/technology/ai/feed/',
        'https://spectrum.ieee.org/topic/artificial-intelligence/rss',
        'https://www.marktechpost.com/feed/', 'https://syncedreview.com/feed/',
        'https://www.johnscra.com/feed/', 'https://www.unite.ai/feed/',
        'https://machinelearningmastery.com/feed/', 'https://towardsdatascience.com/feed',
        'https://www.analyticsvidhya.com/feed/', 'https://www.kdnuggets.com/feed/',
        'https://huggingface.co/blog/feed.xml', 'https://www.databricks.com/feed/category/ai',
        'https://lambdalabs.com/blog/feed.xml', 'https://scale.com/blog/feed.xml',
        'https://research.google/blog/feed/', 'https://aws.amazon.com/blogs/machine-learning/feed/',
        'https://blogs.nvidia.com/feed/', 'https://replicate.com/blog/feed.xml',
        'https://stability.ai/blog/feed.xml', 'https://together.ai/blog/feed.xml',
        'https://hnrss.org/newest?q=transformer+OR+diffusion+OR+RLHF+OR+LoRA+OR+RAG+OR+agentic',
    ]:
        add(a, url, 'rss')

    # ════════════════════════════════════════════════════════════════
    # BUSINESS (~120 sources)
    # ════════════════════════════════════════════════════════════════
    b = 'business'
    for url in [
        'https://www.bloomberg.com/', 'https://www.forbes.com/',
        'https://www.businessinsider.com/', 'https://www.reuters.com/business/',
        'https://www.ft.com/', 'https://www.economist.com/',
        'https://hbr.org/', 'https://www.inc.com/',
        'https://www.entrepreneur.com/', 'https://www.fastcompany.com/',
        'https://www.cnbc.com/', 'https://www.marketwatch.com/',
        'https://www.barrons.com/', 'https://www.nytimes.com/section/business',
        'https://www.wsj.com/', 'https://www.businessnewsdaily.com/',
        'https://www.business2community.com/', 'https://www.smallbiztrends.com/',
        'https://www.business-standard.com/', 'https://www.livemint.com/',
        'https://economictimes.indiatimes.com/', 'https://www.businesstoday.in/',
        'https://www.financialexpress.com/', 'https://www.dealstreetasia.com/',
        'https://asia.nikkei.com/', 'https://www.japantimes.co.jp/business/',
        'https://www.scmp.com/business', 'https://www.caixinglobal.com/',
        'https://www.businessoffashion.com/', 'https://www.modernretail.co/',
        'https://www.restaurantbusinessonline.com/', 'https://www.supplychaindive.com/',
        'https://www.logisticsmgmt.com/', 'https://www.freightwaves.com/',
        'https://www.gartner.com/en/articles', 'https://www.mckinsey.com/featured-insights',
        'https://www.bcg.com/publications', 'https://www.deloitte.com/insights',
        'https://www.pwc.com/gx/en/issues.html', 'https://www.accenture.com/us-en/insights',
    ]:
        add(b, url, 'html', 'h2 a, h3 a, .title a, article a')
    for url in [
        'https://feeds.bloomberg.com/markets/news.rss', 'https://www.forbes.com/business/index.xml',
        'https://feeds.content.dowjones.io/public/rss/mw_topstories',
        'https://feeds.feedburner.com/entrepreneur/latest', 'https://www.inc.com/rss/',
        'https://hbr.org/feed/latest', 'https://www.fastcompany.com/rss',
        'https://www.cnbc.com/id/10001147/device/rss/rss.html',
        'https://feeds.content.dowjones.io/public/rss/wsj_tech', 'https://feeds.bbci.co.uk/news/business/rss.xml',
        'https://www.economist.com/business/rss.xml', 'https://rss.nytimes.com/services/xml/rss/nyt/Business.xml',
        'https://www.ft.com/rss/business-education', 'https://www.reuters.com/agency/business-feed/',
        'https://www.business-standard.com/feed/', 'https://economictimes.indiatimes.com/rssfeeds/13357261.cms',
        'https://feeds.feedburner.com/entrepreneur/latest', 'https://asia.nikkei.com/rss/feed/business',
        'https://www.japantimes.co.jp/feed/business', 'https://www.modernretail.co/feed/',
        'https://www.supplychaindive.com/feeds/news/', 'https://www.freightwaves.com/feed/',
        'https://www.gartner.com/en/articles/feed', 'https://www.mckinsey.com/featured-insights/feed',
    ]:
        add(b, url, 'rss')

    # ════════════════════════════════════════════════════════════════
    # SCIENCE (~100 sources)
    # ════════════════════════════════════════════════════════════════
    sc = 'science'
    for url in [
        'https://www.sciencedaily.com/', 'https://www.nature.com/latest-news',
        'https://www.newscientist.com/', 'https://www.scientificamerican.com/',
        'https://phys.org/', 'https://www.nasa.gov/news/',
        'https://www.esa.int/Science_Exploration', 'https://home.cern/news',
        'https://www.nationalgeographic.com/science/', 'https://www.livescience.com/',
        'https://www.space.com/', 'https://www.astronomy.com/',
        'https://www.sciencenews.org/', 'https://www.eurekalert.org/',
        'https://www.pnas.org/', 'https://www.cell.com/',
        'https://www.the-scientist.com/', 'https://www.quantamagazine.org/',
        'https://arstechnica.com/science/', 'https://www.bbc.com/news/science_and_environment',
        'https://www.theguardian.com/science', 'https://www.newsweek.com/science',
        'https://www.discovermagazine.com/', 'https://www.popsci.com/',
        'https://www.iflscience.com/', 'https://www.zmescience.com/',
        'https://www.sci-news.com/', 'https://www.eurekalert.org/news-releases',
    ]:
        add(sc, url, 'html', 'h2 a, h3 a, .title a, article a')
    for url in [
        'https://www.nature.com/nature.rss', 'https://www.sciencedaily.com/rss/all.xml',
        'https://www.newscientist.com/feed/home', 'https://www.scientificamerican.com/feed/',
        'https://phys.org/rss-feed/', 'https://www.nasa.gov/rss/dyn/breaking_news.rss',
        'https://www.space.com/feed', 'https://www.sciencenews.org/feed/',
        'https://www.eurekalert.org/rss/news_releases.xml', 'https://www.quantamagazine.org/feed/',
        'https://www.pnas.org/action/showFeed?type=etoc', 'https://www.cell.com/cell/rss',
        'https://www.livescience.com/feed', 'https://www.iflscience.com/feed/',
        'https://www.discovermagazine.com/rss.xml', 'https://www.popsci.com/rss/',
        'https://www.zmescience.com/feed/', 'https://feeds.bbci.co.uk/news/science_and_environment/rss.xml',
        'https://www.theguardian.com/science/rss', 'https://www.newsweek.com/rss/science',
    ]:
        add(sc, url, 'rss')

    # ════════════════════════════════════════════════════════════════
    # HEALTH (~80 sources)
    # ════════════════════════════════════════════════════════════════
    h = 'health'
    for url in [
        'https://www.webmd.com/news/default.htm', 'https://www.medicalnewstoday.com/',
        'https://www.healthline.com/', 'https://www.mayoclinic.org/healthy-lifestyle',
        'https://www.cdc.gov/media/', 'https://www.who.int/news-room',
        'https://www.nih.gov/news-events', 'https://www.nejm.org/',
        'https://www.thelancet.com/', 'https://jamanetwork.com/',
        'https://www.bmj.com/', 'https://www.medscape.com/',
        'https://www.everydayhealth.com/', 'https://www.verywellhealth.com/',
        'https://www.health.harvard.edu/blog', 'https://www.medpagetoday.com/',
        'https://www.statnews.com/', 'https://www.fiercehealthcare.com/',
        'https://www.healthcareitnews.com/', 'https://www.modernhealthcare.com/',
        'https://www.advisory.com/daily-briefing', 'https://khn.org/',
        'https://www.phaa.com.au/', 'https://www.pulsetoday.co.uk/',
    ]:
        add(h, url, 'html', 'h2 a, h3 a, .title a, article a')
    for url in [
        'https://rss.nytimes.com/services/xml/rss/nyt/Health.xml',
        'https://www.medicalnewstoday.com/newsletters/rss/headlines',
        'https://www.healthline.com/rss', 'https://www.cdc.gov/media/rss/',
        'https://www.nih.gov/news-events/news-releases/feed.xml',
        'https://www.nejm.org/feed/past-7-days', 'https://www.thelancet.com/rssfeed',
        'https://jamanetwork.com/rss/site_10/TOP.xml', 'https://www.bmj.com/rss',
        'https://www.medscape.com/rss/news', 'https://www.statnews.com/feed/',
        'https://www.fiercehealthcare.com/feed/', 'https://www.healthcareitnews.com/feed/',
        'https://khn.org/feed/', 'https://www.everydayhealth.com/feed/',
    ]:
        add(h, url, 'rss')

    # ════════════════════════════════════════════════════════════════
    # FINANCE (~80 sources)
    # ════════════════════════════════════════════════════════════════
    f = 'finance'
    for url in [
        'https://www.investopedia.com/', 'https://www.coindesk.com/',
        'https://cointelegraph.com/', 'https://www.bloomberg.com/markets',
        'https://www.reuters.com/markets/', 'https://www.cnbc.com/finance/',
        'https://www.marketwatch.com/', 'https://www.barrons.com/',
        'https://finance.yahoo.com/', 'https://www.zerohedge.com/',
        'https://seekingalpha.com/', 'https://www.tradingview.com/news/',
        'https://www.fool.com/', 'https://www.nasdaq.com/news/',
        'https://www.nyse.com/news', 'https://www.sec.gov/news',
        'https://www.federalreserve.gov/newsevents.htm',
        'https://www.imf.org/en/News', 'https://www.worldbank.org/en/news',
        'https://www.weforum.org/agenda/', 'https://www.oecd.org/newsroom/',
        'https://www.warrenfaulkner.com/', 'https://www.dailyfx.com/',
        'https://www.forexfactory.com/', 'https://www.investing.com/analysis',
    ]:
        add(f, url, 'html', 'h2 a, h3 a, .title a, article a')
    for url in [
        'https://feeds.content.dowjones.io/public/rss/mw_topstories',
        'https://www.coindesk.com/feed/', 'https://cointelegraph.com/rss',
        'https://feeds.bloomberg.com/markets/news.rss',
        'https://finance.yahoo.com/rss/', 'https://seekingalpha.com/feed.xml',
        'https://www.fool.com/feed/', 'https://www.nasdaq.com/rss/',
        'https://www.sec.gov/rss/news/press.xml', 'https://www.federalreserve.gov/rss/press.xml',
        'https://www.imf.org/en/News/RSS', 'https://www.weforum.org/feed/agenda.xml',
        'https://www.zerohedge.com/feed', 'https://www.investing.com/rss/news.rss',
        'https://hnrss.org/newest?q=crypto+OR+bitcoin+OR+blockchain+OR+defi+OR+ethereum',
        'https://www.reddit.com/r/cryptocurrency/hot/.rss',
        'https://www.reddit.com/r/wallstreetbets/hot/.rss',
        'https://www.reddit.com/r/investing/hot/.rss',
    ]:
        add(f, url, 'rss')

    # ════════════════════════════════════════════════════════════════
    # ENTERTAINMENT (~70 sources)
    # ════════════════════════════════════════════════════════════════
    e = 'entertainment'
    for url in [
        'https://variety.com/', 'https://www.hollywoodreporter.com/',
        'https://www.billboard.com/', 'https://www.rollingstone.com/',
        'https://pitchfork.com/', 'https://www.nme.com/',
        'https://www.stereogum.com/', 'https://consequence.net/',
        'https://www.spin.com/', 'https://www.avclub.com/',
        'https://www.ign.com/', 'https://www.rottentomatoes.com/',
        'https://www.imdb.com/news/', 'https://www.metacritic.com/',
        'https://www.themoviedb.org/', 'https://deadline.com/',
        'https://www.thewrap.com/', 'https://www.tvguide.com/',
        'https://www.netflix.com/tudum', 'https://www.whats-on-netflix.com/',
        'https://www.youtubetrends.com/', 'https://www.tiktok.com/trending',
        'https://www.instagram.com/explore/', 'https://www.buzzfeed.com/',
        'https://www.upworthy.com/', 'https://www.theonion.com/',
        'https://www.collegehumor.com/', 'https://www.vulture.com/',
    ]:
        add(e, url, 'html', 'h2 a, h3 a, .title a, article a')
    for url in [
        'https://variety.com/feed/', 'https://www.hollywoodreporter.com/feed/',
        'https://www.billboard.com/feed/', 'https://www.rollingstone.com/feed/',
        'https://pitchfork.com/feed/feed.xml', 'https://www.nme.com/feed',
        'https://www.avclub.com/rss', 'https://www.spin.com/feed/',
        'https://consequence.net/feed/', 'https://deadline.com/feed/',
        'https://www.thewrap.com/feed/', 'https://www.vulture.com/rss',
        'https://www.buzzfeed.com/index.xml', 'https://rss.nytimes.com/services/xml/rss/nyt/Arts.xml',
        'https://www.ign.com/feed.xml', 'https://www.rottentomatoes.com/rss/news.xml',
    ]:
        add(e, url, 'rss')

    # ════════════════════════════════════════════════════════════════
    # GAMING (~70 sources)
    # ════════════════════════════════════════════════════════════════
    g = 'gaming'
    for url in [
        'https://www.ign.com/', 'https://www.pcgamer.com/',
        'https://www.eurogamer.net/', 'https://www.gamespot.com/',
        'https://www.polygon.com/', 'https://www.kotaku.com/',
        'https://www.destructoid.com/', 'https://www.rockpapershotgun.com/',
        'https://www.vg247.com/', 'https://www.gamerevolution.com/',
        'https://www.gamesradar.com/', 'https://www.playstation.com/en-us/ps-blog/',
        'https://news.xbox.com/en-us/', 'https://www.nintendo.com/whatsnew/',
        'https://www.gameinformer.com/', 'https://www.gamersnexus.net/',
        'https://www.metacritic.com/game/', 'https://www.opencritic.com/',
        'https://www.twitch.tv/directory', 'https://www.dotesports.com/',
        'https://www.oneesports.gg/', 'https://www.upcomer.com/',
        'https://gameworldobserver.com/', 'https://techraptor.net/',
        'https://www.siliconera.com/', 'https://www.nintendolife.com/',
    ]:
        add(g, url, 'html', 'h2 a, h3 a, .title a, article a')
    for url in [
        'https://www.ign.com/feed.xml', 'https://www.pcgamer.com/rss/',
        'https://www.eurogamer.net/feed', 'https://www.gamespot.com/feeds/news/',
        'https://www.polygon.com/rss/index.xml', 'https://www.kotaku.com/rss',
        'https://www.destructoid.com/feed/', 'https://www.rockpapershotgun.com/feed/',
        'https://www.vg247.com/feed/', 'https://www.gamesradar.com/feed/',
        'https://blog.playstation.com/feed/', 'https://news.xbox.com/feed/',
        'https://www.nintendo.com/whatsnew/feed/', 'https://www.dotesports.com/feed/',
        'https://www.siliconera.com/feed/', 'https://www.nintendolife.com/feed/',
    ]:
        add(g, url, 'rss')

    # ════════════════════════════════════════════════════════════════
    # LIFESTYLE (~60 sources)
    # ════════════════════════════════════════════════════════════════
    l = 'lifestyle'
    for url in [
        'https://www.bustle.com/', 'https://www.self.com/',
        'https://www.refinery29.com/', 'https://www.vogue.com/',
        'https://www.elle.com/', 'https://www.harpersbazaar.com/',
        'https://www.cosmopolitan.com/', 'https://www.glamour.com/',
        'https://www.allure.com/', 'https://www.vanityfair.com/',
        'https://www.instyle.com/', 'https://www.whowhatwear.com/',
        'https://www.byrdie.com/', 'https://www.thecut.com/',
        'https://www.manrepeller.com/', 'https://www.goop.com/',
        'https://www.mindbodygreen.com/', 'https://www.wellandgood.com/',
        'https://www.theeverygirl.com/', 'https://www.apartmenttherapy.com/',
        'https://www.thespruce.com/', 'https://www.architecturaldigest.com/',
        'https://www.designsponge.com/', 'https://www.remodelista.com/',
    ]:
        add(l, url, 'html', 'h2 a, h3 a, .title a, article a')
    for url in [
        'https://www.bustle.com/rss', 'https://www.refinery29.com/rss.xml',
        'https://www.vogue.com/feed/', 'https://www.elle.com/rss/',
        'https://www.cosmopolitan.com/rss/', 'https://www.vanityfair.com/feed/',
        'https://www.thecut.com/feed/', 'https://www.mindbodygreen.com/feed/',
        'https://www.wellandgood.com/feed/', 'https://www.apartmenttherapy.com/feed/',
        'https://www.thespruce.com/feed/', 'https://www.architecturaldigest.com/feed/',
    ]:
        add(l, url, 'rss')

    # ════════════════════════════════════════════════════════════════
    # EDUCATION (~50 sources)
    # ════════════════════════════════════════════════════════════════
    ed = 'education'
    for url in [
        'https://www.edsurge.com/', 'https://www.insidehighered.com/',
        'https://www.chronicle.com/', 'https://www.timeshighereducation.com/',
        'https://www.classcentral.com/', 'https://www.coursera.org/browse',
        'https://www.edx.org/courses', 'https://www.udacity.com/blog',
        'https://www.khanacademy.org/about/blog', 'https://blog.duolingo.com/',
        'https://www.teachthought.com/', 'https://www.edutopia.org/',
        'https://www.edsurge.com/news', 'https://hechingerreport.org/',
        'https://www.the74million.org/', 'https://www.ecampusnews.com/',
        'https://campustechnology.com/', 'https://www.universityworldnews.com/',
        'https://www.topuniversities.com/', 'https://www.qs.com/',
        'https://www.shanghairanking.com/', 'https://www.sciencemag.org/careers',
    ]:
        add(ed, url, 'html', 'h2 a, h3 a, .title a, article a')
    for url in [
        'https://www.edsurge.com/feed', 'https://www.insidehighered.com/feed',
        'https://www.chronicle.com/feed/rss', 'https://www.classcentral.com/feed.xml',
        'https://www.coursera.org/blog/feed', 'https://www.edx.org/feed',
        'https://www.udacity.com/blog/feed', 'https://blog.duolingo.com/feed/',
        'https://www.edutopia.org/feed', 'https://hechingerreport.org/feed/',
        'https://www.the74million.org/feed/', 'https://www.ecampusnews.com/feed/',
        'https://campustechnology.com/feed/', 'https://www.universityworldnews.com/rss/',
    ]:
        add(ed, url, 'rss')

    # ════════════════════════════════════════════════════════════════
    # SPORTS (~80 sources)
    # ════════════════════════════════════════════════════════════════
    sp = 'sports'
    for url in [
        'https://www.espn.com/', 'https://www.theathletic.com/',
        'https://www.si.com/', 'https://bleacherreport.com/',
        'https://www.sportskeeda.com/', 'https://www.cbssports.com/',
        'https://www.nbcsports.com/', 'https://www.foxsports.com/',
        'https://sports.yahoo.com/', 'https://www.goal.com/',
        'https://www.skysports.com/', 'https://www.eurosport.com/',
        'https://www.bbc.com/sport', 'https://www.theguardian.com/sport',
        'https://www.telegraph.co.uk/sport/', 'https://www.independent.co.uk/sport',
        'https://www.marca.com/', 'https://as.com/',
        'https://www.ole.com.ar/', 'https://www.espn.com.br/',
        'https://www.nfl.com/news/', 'https://www.nba.com/news/',
        'https://www.mlb.com/news/', 'https://www.nhl.com/news/',
        'https://www.formula1.com/en/latest', 'https://www.motorsport.com/',
        'https://www.cyclingnews.com/', 'https://www.tennis.com/',
        'https://www.golf.com/', 'https://www.wwe.com/news',
        'https://www.ufc.com/news', 'https://www.sherdog.com/',
    ]:
        add(sp, url, 'html', 'h2 a, h3 a, .title a, article a')
    for url in [
        'https://www.espn.com/espn/rss/news', 'https://bleacherreport.com/rss',
        'https://www.cbssports.com/rss/headlines', 'https://sports.yahoo.com/rss/',
        'https://feeds.bbci.co.uk/sport/rss.xml', 'https://www.theguardian.com/uk/sport/rss',
        'https://www.goal.com/feed', 'https://www.skysports.com/rss/',
        'https://www.marca.com/rss/', 'https://www.nfl.com/feeds/rss/news',
        'https://www.nba.com/rss/news', 'https://www.mlb.com/feeds/news/rss.xml',
        'https://www.nhl.com/rss/news', 'https://www.formula1.com/en/latest.rss',
        'https://www.motorsport.com/rss/', 'https://www.cyclingnews.com/feed/',
        'https://www.tennis.com/feed/', 'https://www.golf.com/feed/',
        'https://www.sportskeeda.com/feed', 'https://www.theathletic.com/rss/',
        'https://sports.yahoo.com/rss/', 'https://www.eurosport.com/rss/',
    ]:
        add(sp, url, 'rss')

    # ════════════════════════════════════════════════════════════════
    # POLITICS (~70 sources)
    # ════════════════════════════════════════════════════════════════
    p = 'politics'
    for url in [
        'https://www.politico.com/', 'https://thehill.com/',
        'https://www.realclearpolitics.com/', 'https://www.fivethirtyeight.com/',
        'https://www.nytimes.com/section/politics', 'https://www.washingtonpost.com/politics/',
        'https://www.theguardian.com/politics', 'https://www.bbc.com/news/politics',
        'https://www.reuters.com/world/', 'https://apnews.com/politics/',
        'https://www.npr.org/sections/politics/', 'https://www.cnn.com/politics/',
        'https://www.foxnews.com/politics', 'https://www.msnbc.com/politics',
        'https://www.c-span.org/', 'https://www.cookpolitical.com/',
        'https://sabatos.crystalball.com/', 'https://www.rasmussenreports.com/',
        'https://www.gallup.com/home.aspx', 'https://www.pewresearch.org/politics/',
        'https://www.brookings.edu/', 'https://www.cfr.org/',
        'https://www.chathamhouse.org/', 'https://www.carnegieendowment.org/',
        'https://www.heritage.org/', 'https://www.aei.org/',
        'https://www.cato.org/', 'https://www.opensocietyfoundations.org/',
    ]:
        add(p, url, 'html', 'h2 a, h3 a, .title a, article a')
    for url in [
        'https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml',
        'https://feeds.washingtonpost.com/rss/politics',
        'https://www.politico.com/rss/politics.xml', 'https://thehill.com/feed/',
        'https://www.bbc.com/news/10628494', 'https://www.theguardian.com/politics/rss',
        'https://feeds.reuters.com/reuters/politicsNews', 'https://apnews.com/politics.rss',
        'https://www.npr.org/rss/politics', 'https://www.cnn.com/rss/politics',
        'https://www.foxnews.com/about/rss/politics/', 'https://www.pewresearch.org/politics/feed/',
        'https://www.brookings.edu/feed/', 'https://www.cfr.org/feed/',
        'https://www.heritage.org/feed', 'https://www.aei.org/feed/',
        'https://www.cato.org/feed/', 'https://www.fivethirtyeight.com/feed/',
        'https://www.realclearpolitics.com/rss/', 'https://www.rasmussenreports.com/rss/',
    ]:
        add(p, url, 'rss')

    # ════════════════════════════════════════════════════════════════
    # GENERAL / NEWS AGGREGATORS (~50 extra)
    # ════════════════════════════════════════════════════════════════
    gen = 'general'
    for url in [
        'https://news.google.com/', 'https://www.reddit.com/r/all/hot/',
        'https://www.digg.com/', 'https://flipboard.com/',
        'https://www.newsnow.co.uk/', 'https://ground.news/',
        'https://news.ycombinator.com/best', 'https://lobste.rs/',
        'https://www.tildes.net/', 'https://www.metafilter.com/',
        'https://www.slashdot.org/', 'https://www.fark.com/',
        'https://www.drudgereport.com/', 'https://www.zerohedge.com/',
        'https://www.oann.com/', 'https://www.breitbart.com/',
        'https://www.dailywire.com/', 'https://www.foxnews.com/',
        'https://www.msnbc.com/', 'https://www.cnn.com/',
        'https://www.abcnews.go.com/', 'https://www.cbsnews.com/',
        'https://www.nbcnews.com/', 'https://www.pbs.org/newshour/',
        'https://www.npr.org/', 'https://www.aljazeera.com/',
        'https://www.dw.com/', 'https://www.france24.com/',
        'https://www.reuters.com/', 'https://apnews.com/',
        'https://www.afp.com/', 'https://www.upi.com/',
        'https://www.voanews.com/', 'https://www.rferl.org/',
        'https://www.bnonews.com/', 'https://www.newsweek.com/',
        'https://www.theatlantic.com/', 'https://www.newyorker.com/',
        'https://www.economist.com/', 'https://www.foreignaffairs.com/',
        'https://www.propublica.org/', 'https://www.motherjones.com/',
        'https://www.thenation.com/', 'https://www.newrepublic.com/',
        'https://www.weeklystandard.com/', 'https://www.nationalreview.com/',
        'https://www.vox.com/', 'https://www.buzzfeednews.com/',
        'https://www.axios.com/', 'https://www.semafor.com/',
    ]:
        add(gen, url, 'html', 'h2 a, h3 a, .title a, article a')
    for url in [
        'https://news.google.com/news/rss/headlines',
        'https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml',
        'https://feeds.bbci.co.uk/news/rss.xml',
        'https://www.theguardian.com/world/rss',
        'https://www.reddit.com/r/all/hot/.rss',
        'https://news.google.com/rss',
        'https://feeds.npr.org/1001/rss.xml',
        'https://www.aljazeera.com/xml/rss/all.xml',
        'https://rss.dw.com/rdf/rss-en-all',
        'https://www.france24.com/en/rss',
        'https://feeds.reuters.com/reuters/topNews',
        'https://abcnews.go.com/abcnews/topstories',
        'https://www.cbsnews.com/latest/rss/',
        'https://feeds.nbcnews.com/nbcnews/public/news',
        'https://www.pbs.org/newshour/feeds/rss/headlines',
        'https://feeds.bbci.co.uk/news/world/rss.xml',
        'https://www.theatlantic.com/feed/all/',
        'https://www.newyorker.com/feed/news',
        'https://feeds.economist.com/economist/feeds/print-sections/77/',
        'https://www.economist.com/feeds/print-sections/77/britain.xml',
        'https://www.vox.com/rss/index.xml',
        'https://www.axios.com/feed/',
        'https://feeds.feedburner.com/Newsweek',
        'https://feeds.feedburner.com/slashdot',
        'https://lobste.rs/rss',
        'https://www.tildes.net/tildes.xml',
    ]:
        add(gen, url, 'rss')

    # ════════════════════════════════════════════════════════════════
    # CRYPTODEFI (~40 sources - new category)
    # ════════════════════════════════════════════════════════════════
    cr = 'crypto'
    for url in [
        'https://cointelegraph.com/', 'https://www.coindesk.com/',
        'https://decrypt.co/', 'https://www.theblock.co/',
        'https://defillama.com/', 'https://debank.com/',
        'https://www.cryptoglobe.com/', 'https://cryptopotato.com/',
        'https://bitcoinmagazine.com/', 'https://bitcoinist.com/',
        'https://www.newsbtc.com/', 'https://u.today/',
        'https://cryptobriefing.com/', 'https://ambcrypto.com/',
        'https://www.trustnodes.com/', 'https://beincrypto.com/',
        'https://cryptonews.com/', 'https://dailyhodl.com/',
        'https://ethereumworldnews.com/', 'https://solana.com/news',
        'https://cardanofeed.com/', 'https://polkadot.network/blog/',
        'https://avax.network/blog', 'https://blog.chain.link/',
        'https://uniswap.org/blog', 'https://aave.com/blog/',
        'https://compound.finance/governance', 'https://makerdao.com/en/feeds/',
        'https://blog.yearn.finance/', 'https://curve.fi/roadmap',
        'https://balancer.fi/blog', 'https://pancakeswap.finance/blog',
        'https://sushichef.medium.com/', 'https://www.okx.com/news',
        'https://www.binance.com/en/blog', 'https://blog.kraken.com/',
        'https://blog.coinbase.com/', 'https://www.gemini.com/blog',
        'https://www.bybit.com/en/blog', 'https://www.bitfinex.com/blog',
        'https://www.ledger.com/blog', 'https://blog.trezor.io/',
    ]:
        add(cr, url, 'html', 'h2 a, h3 a, .title a, article a')
    for url in [
        'https://cointelegraph.com/rss', 'https://www.coindesk.com/feed/',
        'https://decrypt.co/feed', 'https://www.theblock.co/rss',
        'https://cryptopotato.com/feed/', 'https://bitcoinmagazine.com/feed/',
        'https://u.today/rss', 'https://cryptobriefing.com/feed/',
        'https://beincrypto.com/feed/', 'https://dailyhodl.com/feed/',
        'https://blog.chain.link/feed/', 'https://blog.coinbase.com/feed',
        'https://blog.kraken.com/feed', 'https://www.gemini.com/blog/feed',
        'https://blog.uniswap.org/feed.xml', 'https://aave.com/blog/feed',
        'https://blog.trezor.io/feed',
    ]:
        add(cr, url, 'rss')

    # ════════════════════════════════════════════════════════════════
    # DESIGN (~30 sources - new category)
    # ════════════════════════════════════════════════════════════════
    d = 'design'
    for url in [
        'https://www.behance.net/', 'https://dribbble.com/stories',
        'https://www.awwwards.com/', 'https://www.siteinspire.com/',
        'https://www.designernews.co/', 'https://medium.com/tag/design',
        'https://www.smashingmagazine.com/', 'https://alistapart.com/',
        'https://uxdesign.cc/', 'https://www.nngroup.com/articles/',
        'https://www.interaction-design.org/literature',
        'https://www.creativebloq.com/', 'https://www.designweek.co.uk/',
        'https://www.dezeen.com/', 'https://www.archdaily.com/',
        'https://www.yankodesign.com/', 'https://www.core77.com/',
        'https://www.design-milk.com/', 'https://www.colossally.com/',
        'https://www.itsnicethat.com/', 'https://www.creativeboom.com/',
    ]:
        add(d, url, 'html', 'h2 a, h3 a, .title a, article a')
    for url in [
        'https://dribbble.com/stories.rss', 'https://www.awwwards.com/feed/',
        'https://uxdesign.cc/feed', 'https://www.smashingmagazine.com/feed/',
        'https://alistapart.com/main/feed/', 'https://www.creativebloq.com/rss',
        'https://www.dezeen.com/feed/', 'https://www.archdaily.com/feed',
        'https://www.design-milk.com/feed/', 'https://www.itsnicethat.com/feed',
        'https://www.creativeboom.com/feed/',
    ]:
        add(d, url, 'rss')

    # ════════════════════════════════════════════════════════════════
    # ENVIRONMENT/CLIMATE (~30 sources - new category)
    # ════════════════════════════════════════════════════════════════
    env = 'environment'
    for url in [
        'https://www.climatecentral.org/', 'https://insideclimatenews.org/',
        'https://www.carbonbrief.org/', 'https://earther.gizmodo.com/',
        'https://www.theguardian.com/environment', 'https://www.bbc.com/news/science-environment',
        'https://www.nationalgeographic.com/environment/', 'https://www.worldwildlife.org/stories',
        'https://www.greenpeace.org/international/stories/',
        'https://www.wwf.org.uk/news', 'https://350.org/press/',
        'https://www.sierraclub.org/articles', 'https://www.nrdc.org/stories',
        'https://www.edf.org/news', 'https://www.ucsusa.org/resources',
        'https://www.wri.org/news', 'https://www.ipcc.ch/news/',
        'https://unfccc.int/news', 'https://www.climate.gov/news-features',
        'https://www.epa.gov/newsroom', 'https://www.noaa.gov/news',
        'https://earthobservatory.nasa.gov/', 'https://www.climateaction.org/',
        'https://www.greenbiz.com/', 'https://www.canarymedia.com/',
        'https://www.utilitydive.com/', 'https://www.rechargenews.com/',
        'https://www.pv-magazine.com/', 'https://www.windpowermonthly.com/',
    ]:
        add(env, url, 'html', 'h2 a, h3 a, .title a, article a')
    for url in [
        'https://insideclimatenews.org/feed/', 'https://www.carbonbrief.org/feed/',
        'https://www.theguardian.com/environment/rss', 'https://www.greenbiz.com/feed/',
        'https://www.canarymedia.com/feed', 'https://www.utilitydive.com/feeds/news/',
        'https://www.rechargenews.com/feed', 'https://www.pv-magazine.com/feed/',
        'https://www.climatecentral.org/feed/', 'https://www.nrdc.org/rss',
        'https://www.wri.org/news/rss', 'https://www.noaa.gov/news/rss',
    ]:
        add(env, url, 'rss')

    # ════════════════════════════════════════════════════════════════
    # SPACE (~25 sources - new category)
    # ════════════════════════════════════════════════════════════════
    spc = 'space'
    for url in [
        'https://www.space.com/', 'https://www.astronomy.com/',
        'https://www.nasa.gov/news/', 'https://www.esa.int/Science_Exploration',
        'https://www.spacex.com/updates/', 'https://www.blueorigin.com/news',
        'https://spacenews.com/', 'https://www.spaceflightnow.com/',
        'https://www.planetary.org/articles', 'https://skyandtelescope.org/',
        'https://www.spaceweather.com/', 'https://www.seti.org/press-release',
        'https://www.jpl.nasa.gov/news/', 'https://www.spacepolicyonline.com/',
        'https://www.space.commercialization.com/', 'https://www.rocketlabusa.com/news/',
        'https://www.relativityspace.com/blog', 'https://www.virgingalactic.com/news/',
    ]:
        add(spc, url, 'html', 'h2 a, h3 a, .title a, article a')
    for url in [
        'https://www.space.com/feed', 'https://www.nasa.gov/rss/dyn/breaking_news.rss',
        'https://spacenews.com/feed/', 'https://www.spaceflightnow.com/feed/',
        'https://www.planetary.org/rss.xml', 'https://skyandtelescope.org/feed/',
        'https://www.jpl.nasa.gov/feeds/news', 'https://www.rocketlabusa.com/news/feed/',
    ]:
        add(spc, url, 'rss')

    # ════════════════════════════════════════════════════════════════
    # FOOD (~25 sources - new category)
    # ════════════════════════════════════════════════════════════════
    food = 'food'
    for url in [
        'https://www.foodandwine.com/', 'https://www.bonappetit.com/',
        'https://www.seriouseats.com/', 'https://www.epicurious.com/',
        'https://www.eater.com/', 'https://www.thekitchn.com/',
        'https://www.simplyrecipes.com/', 'https://www.allrecipes.com/',
        'https://www.kingarthurbaking.com/blog', 'https://www.nytimes.com/section/food',
        'https://www.theguardian.com/food', 'https://www.saveur.com/',
        'https://www.food52.com/', 'https://www.101cookbooks.com/',
        'https://www.smittenkitchen.com/', 'https://www.minimalistbaker.com/',
        'https://www.loveandlemons.com/', 'https://www.healthline.com/nutrition',
        'https://www.nutrition.org.uk/news/', 'https://www.foodnavigator.com/',
        'https://www.foodbev.com/', 'https://www.newfoodmagazine.com/',
        'https://www.restaurantdive.com/', 'https://www.tastingtable.com/',
    ]:
        add(food, url, 'html', 'h2 a, h3 a, .title a, article a')
    for url in [
        'https://www.bonappetit.com/feed/', 'https://www.seriouseats.com/feed/',
        'https://www.eater.com/rss/index.xml', 'https://www.thekitchn.com/feed/',
        'https://www.saveur.com/feed/', 'https://www.food52.com/feed/',
        'https://www.foodnavigator.com/RSS/News', 'https://www.foodbev.com/feed/',
        'https://www.restaurantdive.com/feeds/news/', 'https://www.tastingtable.com/feed/',
    ]:
        add(food, url, 'rss')

    # ════════════════════════════════════════════════════════════════
    # TRAVEL (~25 sources - new category)
    # ════════════════════════════════════════════════════════════════
    tr = 'travel'
    for url in [
        'https://www.lonelyplanet.com/news', 'https://www.travelandleisure.com/',
        'https://www.cntraveler.com/', 'https://www.nationalgeographic.com/travel/',
        'https://www.frommers.com/', 'https://www.ricksteves.com/news',
        'https://www.nomadicmatt.com/', 'https://www.legalnomads.com/',
        'https://www.worldtravelguide.net/', 'https://www.travelweekly.com/',
        'https://skift.com/', 'https://www.phocuswire.com/',
        'https://www.tnooz.com/', 'https://www.hospitalitynet.org/',
        'https://www.hotelnewsresource.com/', 'https://www.airlineratings.com/',
        'https://www.flightglobal.com/', 'https://www.thetravel.com/',
        'https://www.tripadvisor.com/blog', 'https://www.booking.com/articles',
        'https://www.airbnb.com/blog/travel', 'https://www.visitbritain.com/us/en/news',
    ]:
        add(tr, url, 'html', 'h2 a, h3 a, .title a, article a')
    for url in [
        'https://www.lonelyplanet.com/news/feed/', 'https://www.travelandleisure.com/feed/',
        'https://www.cntraveler.com/feed/', 'https://skift.com/feed/',
        'https://www.phocuswire.com/feed/', 'https://www.travelweekly.com/RSS/RSSList.aspx',
        'https://www.nomadicmatt.com/feed/', 'https://www.airlineratings.com/feed/',
    ]:
        add(tr, url, 'rss')

    # ════════════════════════════════════════════════════════════════
    # FASHION (~20 sources - new category)
    # ════════════════════════════════════════════════════════════════
    fash = 'fashion'
    for url in [
        'https://www.vogue.com/', 'https://www.harpersbazaar.com/',
        'https://www.elle.com/', 'https://www.cosmopolitan.com/',
        'https://www.glamour.com/', 'https://www.allure.com/',
        'https://www.wwd.com/', 'https://www.businessoffashion.com/',
        'https://www.thefashionlaw.com/', 'https://fashionista.com/',
        'https://www.refinery29.com/', 'https://www.whowhatwear.com/',
        'https://www.byrdie.com/', 'https://www.thecut.com/fashion',
        'https://www.gq.com/', 'https://www.esquire.com/style',
        'https://www.mrporter.com/journal', 'https://www.ssense.com/en-us/editorial',
        'https://www.grailed.com/journal', 'https://www.highsnobiety.com/fashion/',
    ]:
        add(fash, url, 'html', 'h2 a, h3 a, .title a, article a')
    for url in [
        'https://www.vogue.com/feed/', 'https://www.harpersbazaar.com/rss/',
        'https://www.elle.com/rss/', 'https://www.wwd.com/feed/',
        'https://www.businessoffashion.com/feed/', 'https://fashionista.com/feed/',
        'https://www.gq.com/feed/', 'https://www.highsnobiety.com/feed/',
    ]:
        add(fash, url, 'rss')

    # ════════════════════════════════════════════════════════════════
    # HISTORY/MYSTERY (~15 sources - new category)
    # ════════════════════════════════════════════════════════════════
    hist = 'history'
    for url in [
        'https://www.history.com/news', 'https://www.smithsonianmag.com/history/',
        'https://www.ancient-origins.net/', 'https://www.archaeology.org/',
        'https://www.livescience.com/history', 'https://www.bbc.com/news/magazine',
        'https://allthatsinteresting.com/', 'https://www.historicmysteries.com/',
        'https://www.atlasobscura.com/', 'https://www.thehistoryblog.com/',
        'https://warfarehistorynetwork.com/', 'https://www.historynet.com/',
        'https://www.nationalgeographic.com/history/', 'https://www.worldhistory.org/',
    ]:
        add(hist, url, 'html', 'h2 a, h3 a, .title a, article a')
    for url in [
        'https://www.history.com/feed', 'https://www.smithsonianmag.com/rss/history/',
        'https://www.ancient-origins.net/feed', 'https://www.archaeology.org/rss',
        'https://allthatsinteresting.com/feed', 'https://www.atlasobscura.com/feed',
        'https://www.historynet.com/feed/', 'https://www.worldhistory.org/feed.xml',
    ]:
        add(hist, url, 'rss')

    return dict(s)


# ─── Merge with discovered sources ─────────────────────────────────────

_TRENDING_SOURCES_CACHE: Optional[Dict[str, List[Dict]]] = None

def _expand_with_discovery(sources: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
    """Merge pattern-generated sources (10,000+) into the trending sources."""
    global _TRENDING_SOURCES_CACHE
    if _TRENDING_SOURCES_CACHE is not None:
        return _TRENDING_SOURCES_CACHE

    logger.info("Expanding trending sources with pattern discovery (10k+)...")
    try:
        from vagent.source_discovery import SourceDiscovery
        discovery = SourceDiscovery()
        pattern_sources = discovery.generate_pattern_sources()
        # Add sources in bulk per category (fast)
        for cat, s_list in pattern_sources.items():
            rss_urls = []
            html_urls = []
            for s in s_list:
                if s.get('type') == 'rss':
                    rss_urls.append(s['url'])
                else:
                    html_urls.append(s['url'])
            if rss_urls:
                discovery.add_sources_bulk(cat, rss_urls, 'rss')
            if html_urls:
                discovery.add_sources_bulk(cat, html_urls, 'html')

        result = discovery.merge_into_trending_sources(sources, max_per_category=5000)
        total = sum(len(v) for v in result.values())
        logger.info(f"Sources expanded to {total} across {len(result)} categories")
        _TRENDING_SOURCES_CACHE = result
        return result
    except Exception as e:
        logger.warning(f"Source discovery expansion skipped: {e}")
        _TRENDING_SOURCES_CACHE = sources
        return sources


TRENDING_SOURCES: Dict[str, List[Dict]] = _build_trending_sources()  # Start with manual only
_EXPANDED = False

def get_trending_sources() -> Dict[str, List[Dict]]:
    """Get trending sources, expanding to 10k+ on first call."""
    global _EXPANDED
    if not _EXPANDED:
        expanded = _expand_with_discovery(TRENDING_SOURCES)
        TRENDING_SOURCES.update(expanded)
        _EXPANDED = True
    return TRENDING_SOURCES

# ─── Article Model ───────────────────────────────────────────────────────

class WebArticle:
    """Represents a scraped article from a web source."""
    def __init__(self, title: str, url: str, source: str, summary: str = "",
                 category: str = "general", published: Optional[datetime] = None,
                 content: str = ""):
        self.title = title.strip() if title else ""
        self.url = url
        self.source = source
        self.summary = summary
        self.category = category
        self.published = published or datetime.now()
        self.content = content
        self.id = hashlib.md5(url.encode()).hexdigest()[:12]

    def __repr__(self): return f"WebArticle({self.title[:40]}, {self.category})"

    def to_dict(self) -> dict:
        return {
            'title': self.title, 'url': self.url, 'source': self.source,
            'summary': self.summary[:500], 'category': self.category,
            'published': self.published.isoformat() if self.published else None,
        }


# ─── Main Web Scraper ───────────────────────────────────────────────────

class WebScraper:
    """Large-scale concurrent web scraper for trending content."""

    def __init__(self, max_concurrent: int = 50, timeout: float = 15.0):
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self._seen_urls: Set[str] = set()
        self._rate_limiter = DomainRateLimiter(min_interval=0.5)
        self._sem = asyncio.Semaphore(max_concurrent)
        self._http: Optional[httpx.AsyncClient] = None
        self._source_cache: Dict[str, Tuple[float, List[WebArticle]]] = {}

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                timeout=self.timeout, follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=50, max_connections=100),
                headers={
                    'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                                   '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                },
            )
        return self._http

    async def scrape_all_categories(self, max_articles: int = 5000) -> List[WebArticle]:
        """Scrape all categories in parallel with concurrency control."""
        all_articles = []

        # Build all scrape tasks from expanded sources
        all_sources = []
        trending = get_trending_sources()
        for category, sources in trending.items():
            # Limit sources per category to avoid overload
            for source in sources[:min(len(sources), max(50, max_articles // len(trending)))]:
                all_sources.append((source, category))

        random.shuffle(all_sources)

        logger.info(f"Starting scrape of {len(all_sources)} sources across "
                     f"{len(trending)} categories")

        sem = asyncio.Semaphore(self.max_concurrent)

        async def _scrape_one(source: Dict, category: str) -> List[WebArticle]:
            async with sem:
                return await self._scrape_source(source, category)

        # Stream results as they complete
        tasks = [_scrape_one(src, cat) for src, cat in all_sources]
        done = 0
        for coro in asyncio.as_completed(tasks):
            try:
                articles = await coro
                if articles:
                    all_articles.extend(articles)
                    if len(all_articles) >= max_articles:
                        remaining = [t for t in tasks if not t.done()]
                        for t in remaining:
                            t.cancel()
                        break
            except (asyncio.CancelledError, Exception):
                pass
            done += 1
            if done % 100 == 0:
                logger.info(f"Progress: {done}/{len(tasks)} sources → {len(all_articles)} articles")

        # Deduplicate by URL
        seen: Set[str] = set()
        unique = []
        for a in all_articles:
            if a.url not in seen:
                seen.add(a.url)
                unique.append(a)
                if len(unique) >= max_articles:
                    break

        logger.info(f"Scraped {len(unique)} unique articles from {len(all_sources)} sources")
        return unique

    async def scrape_category(self, category: str, max_articles: int = 200) -> List[WebArticle]:
        """Scrape sources for a single category."""
        sources = get_trending_sources().get(category, [])
        if not sources:
            logger.warning(f"No sources for category: {category}")
            return []

        all_articles = []
        sem = asyncio.Semaphore(self.max_concurrent)

        async def _scrape_one(source: Dict) -> List[WebArticle]:
            async with sem:
                return await self._scrape_source(source, category)

        # Shuffle sources for diversity, stop early when we have enough articles
        shuffled = random.sample(sources, min(len(sources), max_articles * 5))
        tasks = [_scrape_one(src) for src in shuffled]
        for coro in asyncio.as_completed(tasks):
            try:
                articles = await coro
                if articles:
                    all_articles.extend(articles)
                    if len(all_articles) >= max_articles:
                        break
            except Exception:
                pass

        # Deduplicate
        seen: Set[str] = set()
        unique = []
        for a in all_articles:
            if a.url not in seen:
                seen.add(a.url)
                unique.append(a)
                if len(unique) >= max_articles:
                    break

        logger.info(f"Scraped {len(unique)} articles for category '{category}'")
        return unique

    async def _scrape_source(self, source: Dict, category: str) -> List[WebArticle]:
        """Scrape a single source and return articles."""
        url = source['url']
        stype = source.get('type', 'rss')
        domain = urlparse(url).netloc

        # Rate limit check
        await self._rate_limiter.acquire(url)

        try:
            client = await self._client()
            resp = await client.get(url)
            resp.raise_for_status()

            self._rate_limiter.report_success(url)

            if stype == 'rss':
                articles = self._parse_rss(resp.text, domain, category)
            else:
                selector = source.get('selector', 'h2 a, h3 a')
                articles = self._parse_html(resp.text, url, selector, domain, category)

            for a in articles:
                if a.url not in self._seen_urls:
                    self._seen_urls.add(a.url)

            return articles

        except Exception as e:
            self._rate_limiter.report_failure(url)
            logger.debug(f"Failed to scrape {url}: {e}")
            return []

    def _parse_rss(self, content: str, domain: str, category: str) -> List[WebArticle]:
        """Parse RSS XML content."""
        import feedparser
        articles = []
        try:
            feed = feedparser.parse(content)
            for entry in feed.entries[:50]:
                title = entry.get('title', '')
                link = entry.get('link', '')
                if not title or not link:
                    continue
                summary = entry.get('summary', '') or entry.get('description', '') or ''
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        published = datetime(*entry.published_parsed[:6])
                    except Exception:
                        pass
                articles.append(WebArticle(
                    title=title, url=link, source=domain,
                    summary=summary, category=category, published=published,
                ))
        except Exception as e:
            logger.debug(f"RSS parse error for {domain}: {e}")
        return articles

    def _parse_html(self, content: str, base_url: str, selector: str,
                    domain: str, category: str) -> List[WebArticle]:
        """Parse HTML content using CSS selectors."""
        articles = []
        try:
            soup = BeautifulSoup(content, 'lxml')
            for link in soup.select(selector):
                href = link.get('href', '')
                title = link.get_text(strip=True)
                if not title or not href or len(title) < 10:
                    continue
                full_url = urljoin(base_url, href)
                articles.append(WebArticle(
                    title=title, url=full_url, source=domain, category=category,
                ))
        except Exception as e:
            logger.debug(f"HTML parse error for {domain}: {e}")
        return articles

    async def cleanup(self):
        if self._http:
            await self._http.aclose()
            self._http = None


# ─── Content Extractor ───────────────────────────────────────────────────

class ContentExtractor:
    """Extracts full readable content from article URLs."""

    def __init__(self, timeout: float = 15.0):
        self._http: Optional[httpx.AsyncClient] = None
        self.timeout = timeout

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self.timeout, follow_redirects=True,
                                            headers={
                                                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                                            })
        return self._http

    async def extract(self, url: str) -> Dict:
        """Extract readable content from a URL. Returns dict with 'url', 'title', 'content'."""
        try:
            client = await self._client()
            resp = await client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'lxml')

            title = ''
            for tag in soup.select('h1, title, .article-title, .entry-title, .post-title'):
                t = tag.get_text(strip=True)
                if t and len(t) > 5:
                    title = t
                    break

            # Remove non-content elements
            for tag in soup.select('script, style, nav, footer, header, .sidebar, .ad, iframe'):
                tag.decompose()

            # Extract main content
            content = ''
            for tag in soup.select('article, .article-body, .entry-content, .post-content, '
                                    '.story-body, .content, main, [role="main"]'):
                paragraphs = tag.select('p, h2, h3, h4, li')
                content = '\n\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
                if len(content) > 200:
                    break

            if not content:
                paragraphs = soup.select('p')
                content = '\n\n'.join(p.get_text(strip=True) for p in paragraphs
                                      if len(p.get_text(strip=True)) > 40)

            return {'url': url, 'title': title, 'content': content[:10000]}
        except Exception as e:
            return {'url': url, 'title': '', 'content': '', 'error': str(e)}

    async def cleanup(self):
        if self._http:
            await self._http.aclose()
            self._http = None


# ─── Trend Aggregator ────────────────────────────────────────────────────

class TrendAggregator:
    """Analyzes scraped articles to identify trending topics and patterns."""

    def __init__(self):
        self._keywords = self._build_keywords()

    def _build_keywords(self) -> Dict[str, float]:
        return {
            # High-weight topic triggers
            'breakthrough': 2.0, 'revolutionary': 1.8, 'game-changing': 1.8,
            'major announcement': 1.5, 'new study': 1.5, 'significant': 1.5,
            'launch': 1.3, 'release': 1.3, 'announced': 1.3, 'unveiled': 1.3,
            'surge': 1.5, 'crash': 1.5, 'record': 1.3, 'milestone': 1.5,
            'ban': 1.5, 'regulation': 1.3, 'scandal': 1.5, 'controversy': 1.5,
            'acquisition': 1.5, 'ipo': 1.5, 'merger': 1.5, 'partnership': 1.3,
            'funding': 1.3, 'investment': 1.3, 'valuation': 1.5,
            # Standard weight
            'AI': 1.0, 'pandemic': 1.0, 'climate': 1.0, 'election': 1.0,
            'war': 1.0, 'peace': 1.0, 'crisis': 1.0, 'innovation': 1.0,
        }

    def find_trends(self, articles: List[WebArticle], min_occurrences: int = 1) -> List[Dict]:
        """Find trending topics by analyzing article titles and content."""
        topic_counts: Dict[str, int] = {}
        topic_articles: Dict[str, List[WebArticle]] = {}
        topic_categories: Dict[str, List[str]] = {}
        topic_dates: Dict[str, List[datetime]] = {}

        TREND_KEYWORDS = self._keywords

        # Weighted topic extraction
        for article in articles:
            text = (article.title + ' ' + article.summary).lower()
            words = re.findall(r'\b[a-z]{3,}\b', text)

            # Check for known keywords first
            for keyword, weight in TREND_KEYWORDS.items():
                if keyword.lower() in text:
                    phrase = keyword.lower()
                    if phrase not in topic_counts:
                        topic_counts[phrase] = 0
                        topic_articles[phrase] = []
                        topic_categories[phrase] = []
                        topic_dates[phrase] = []
                    topic_counts[phrase] += weight
                    topic_articles[phrase].append(article)
                    if article.category not in topic_categories[phrase]:
                        topic_categories[phrase].append(article.category)
                    if article.published:
                        topic_dates[phrase].append(article.published)

            # Extract noun phrases (bigrams and trigrams)
            for i in range(len(words) - 1):
                bigram = f"{words[i]} {words[i+1]}"
                self._score_phrase(bigram, topic_counts, topic_articles, topic_categories,
                                    topic_dates, article, 0.5)
            for i in range(len(words) - 2):
                trigram = f"{words[i]} {words[i+1]} {words[i+2]}"
                self._score_phrase(trigram, topic_counts, topic_articles, topic_categories,
                                    topic_dates, article, 0.3)

        # Build trend dicts
        now = datetime.now()
        trends = []
        for phrase in sorted(topic_counts, key=lambda p: topic_counts[p], reverse=True):
            freq = topic_counts[phrase]
            if freq < min_occurrences:
                continue

            categories = topic_categories.get(phrase, [])
            dates = topic_dates.get(phrase, [])
            articles_list = topic_articles.get(phrase, [])

            # Calculate recency boost
            recent = sum(1 for d in dates if (now - d).days < 2)
            recency_boost = min(2.0, recent * 0.5)

            # Diversity boost
            diversity = min(1.5, len(set(categories)) * 0.3)

            score = freq * (1 + recency_boost) * (1 + diversity)
            dominant_cat = max(set(categories), key=categories.count) if categories else 'general'

            trends.append({
                'topic': phrase,
                'frequency': freq,
                'score': score,
                'category': dominant_cat,
                'categories': list(set(categories)),
                'search_volume': freq * 10,
                'category_diversity': len(set(categories)),
                'recency_score': recency_boost,
                'predicted_trajectory': 'rising' if recency_boost > 1.0 else 'emerging' if freq > 2 else 'steady',
                'urls': [a.url for a in articles_list[:5]],
                'articles': articles_list,
            })

        trends.sort(key=lambda t: t['score'], reverse=True)
        return trends

    def _score_phrase(self, phrase: str, counts: Dict, articles: Dict,
                      categories: Dict, dates: Dict, article: WebArticle, weight: float):
        if phrase in counts:
            counts[phrase] += weight
            articles[phrase].append(article)
            if article.category not in categories[phrase]:
                categories[phrase].append(article.category)
            if article.published:
                dates[phrase].append(article.published)
