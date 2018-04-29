# encoding=utf-8
import requests
from bs4 import BeautifulSoup
import re,urlparse,os
import sys

INPUT_SIGN="{{__INPUT__}}"
headers={"User-Agent":"Mozilla/5.0 (Windows NT 6.3; Win64; x64; rv:56.0) Gecko/20100101 Firefox/56.0",
         "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
         "Accept-Language":"zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
         "Accept-Encoding":""}
REWRITE_TYPE=["normal","path"]

class crawler:
    def __init__(self,url,deepest=5): #���û��ڹ�ȵ������㷨��Ĭ�Ϲ涨������ֵΪ5
        self.host=url
        self.url_rewrite_type=self.url_rewrite_type()
        self.list_opt=list_opt()
        self.deepest=deepest
        self.list_opt.add_url_to_unvisited(url)
        self.url_count_at_one_depth = 1
        self.depth=1

    def url_rewrite_type(self):
        return REWRITE_TYPE[0] #todo:�ж�urlrewriteģʽ
        # ��ǰĬ��Ϊ��ͨģʽ

    def crawl(self):
        while self.depth<=self.deepest and self.list_opt.count_unvisited() > 0:
#            print self.list_opt.get_unvisted()
            html=self.request(self.list_opt.unvisited[0])
            urllist=self.graburl(html)
            for url in urllist:
                if (not self.exists_or_similar(url)):
                    self.list_opt.unvisited.append(url)
            if self.url_count_at_one_depth==0:
                self.depth+=1
            self.url_count_at_one_depth+=len(urllist)
        return self.list_opt.get_visited()

    def request(self,url):
        req=requests.session()
        print "requesting to "+url
        try:
            html=req.get(url,headers=headers).content
        except: Exception
        query_string=urlparse.urlparse(url).query
#        query_args={[(k,v[0]) for k,v in urlparse.parse_qs(query_string).items()]} #�õ����е�queryֵȻ��תΪdict
        self.url_count_at_one_depth-=1
        self.list_opt.unvisited.remove(url)
        self.list_opt.visited.append(url)
#        self.list_opt.visited_url_args_map.append({url:query_args})
        self.list_opt.current_url=url
        return html

    def graburl(self,html):
        urllist = []
        soup=BeautifulSoup(html,"lxml")
        adomlist = soup.findAll("a", {"href": re.compile(".*")})
        formdomlist=soup.findAll("form",{"action":re.compile(".*")})
        for form in formdomlist:
            if (not form.attrs.has_key("method")) or form.attrs["method"].lower()=="get":#ֻȡmethodΪget�ı�
                inputlist=form.select("input")
                formGeneratedUrl=self.parse_form_path(form.attrs["action"])+"?"
                for singleinput in inputlist:
                    if singleinput.attrs.has_key("name"):
                        if singleinput.attrs.has_key("value"):
                            if singleinput.attrs.has_key("type") and singleinput.attrs["type"].lower()=="hidden":
                                formGeneratedUrl+= singleinput.attrs["name"]+"="+singleinput.attrs["value"]+"&"
                            else:
                                formGeneratedUrl += singleinput.attrs["name"]+"="+INPUT_SIGN+"&" #�������������û��ɿص�input�ֶα���INPUT_SIGN
                formGeneratedUrl=formGeneratedUrl[:-1]
            else:
                formGeneratedUrl=self.parse_form_path(form.attrs["action"])
            urllist.append(formGeneratedUrl)

        for i in adomlist:
         url = self.evaluate_and_parse_url(i.attrs["href"])
         if url:
            urllist.append(url)
        return urllist

    def exists_or_similar(self,url):
        #�ж�url�Ƿ��Ѿ����ѷ����б��δ�����б����
        if url in self.list_opt.get_unvisted() or url in self.list_opt.get_visited():
            return True
		#todo: �ж�url�Ƿ�����ǰ������
			
    def evaluate_and_parse_url(self,url):
        if url.startswith(self.host):
            return url
        elif not re.match(r"^(\S+):", url):#�ų�αЭ���Լ�host֮�����վ
            return urlparse.urljoin(self.host,url)
        else :return False

    def parse_form_path(self,formaction):
        #��//Ϊ��ͷ��form actionֵ ��ʾhttp/https
        if formaction.startswith("//"):
            schema=urlparse.urlparse(self.host)[0]
            url=schema+":"+formaction
            if url.startswith(self.host):
                return url
         #��/Ϊ��ʼ��form actionֵ ��ʾ����վ��Ŀ¼
        elif formaction.startswith("/"):
            return self.host+formaction
        #�ж�����index.php��form actionֵ
        else:
            parselist=urlparse.urlparse(self.list_opt.get_current_url())
            parsed_path=parselist.path
            if parselist.path.endswith("/"):
                parsed_path=parselist.path[:-1]
            path=os.path.split(parselist.path)[0]
            return self.host+urlparse.urljoin(path,formaction)

class list_opt:
    def __init__(self):
        self.visited = []
        self.unvisited = []
        self.current_url=""
        self.visited_url_args_map = {}

    def add_url_to_unvisited(self,url):
        self.unvisited.append(url)
    def add_url_to_visited(self,url):
        self.visited.append(url)
    def get_unvisted(self):
        return self.unvisited
    def count_unvisited(self):
        return len(self.unvisited)
    def get_visited(self):
        return self.visited
    def get_current_url(self):
        return self.current_url


if __name__ =="__main__":
    host=sys.argv[1]
    c=crawler(host)
    print crawler.crawl(c)