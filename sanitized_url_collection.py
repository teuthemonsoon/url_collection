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
    def __init__(self,url,deepest=5): #采用基于广度的搜索算法，默认规定深度最大值为5
        self.host=url
        self.url_rewrite_type=self.url_rewrite_type()
        self.list_opt=list_opt()
        self.deepest=deepest
        self.list_opt.add_url_to_unvisited(url)
        self.url_count_at_one_depth = 1
        self.depth=1

    def url_rewrite_type(self):
        return REWRITE_TYPE[0] #todo:判断urlrewrite模式
        # 当前默认为普通模式

    def crawl(self):
        while self.depth<=self.deepest and self.list_opt.count_unvisited() > 0:
#            print self.list_opt.get_unvisted()
            return_html=self.request(self.list_opt.unvisited[0])
            if return_html == False:
                continue
            urllist=self.graburl(return_html)
            for url in urllist:
                query_string = urlparse.urlparse(url).query
                query_args = dict([(k, v[0]) for k, v in urlparse.parse_qs(query_string).items()])  # 得到所有的query值然后转为dict
                query_path = urlparse.urlparse(url).path

                if (not self.exists_or_similar(url)):
                    self.list_opt.unvisited.append(url)
                    self.list_opt.visited_url_args_map.setdefault(query_path, []).append(query_args)
                    # {'path1': [{'param2': 'aaa', 'param1': 'www'}, {'param2': 'bbb', 'param1': 'www'}]}
            if self.url_count_at_one_depth==0:
                self.depth+=1
            self.url_count_at_one_depth+=len(urllist)
        return self.list_opt.get_visited()

    def request(self,url):
        req=requests.session()
        print "requesting to "+url
        try:
            return_html=req.get(url,headers=headers,timeout=4,allow_redirects=False).content
        except requests.exceptions.Timeout or requests.exceptions.ConnectionError:
            print "request to "+url+" failed..retrying..."
            for i in xrange(1,2):
                retry=requests.get(url,headers,timeout=3,allow_redirects=False)
                if retry.status_code:
                    return_html=retry.content
                    break
            return False
        except Exception:
            print "requests unknown error,probobly network error or your ip has been banned."
            return False
        self.url_count_at_one_depth-=1
        self.list_opt.unvisited.remove(url)
        self.list_opt.visited.append(url)
        self.list_opt.current_url=url
        return return_html

    def graburl(self,html):
        urllist = []
        soup=BeautifulSoup(html,"lxml")
        adomlist = soup.findAll("a", {"href": re.compile(".*")})
        formdomlist=soup.findAll("form",{"action":re.compile(".*")})

        for form in formdomlist:
            parsed_path = self.parse_form_path(form.attrs["action"])
            if parsed_path == False:
                continue
            if (not form.attrs.has_key("method")) or form.attrs["method"].lower()=="get":#只取method为get的表单
                inputlist=form.select("input")
                formGeneratedUrl=parsed_path+"?"
                for singleinput in inputlist:
                    if singleinput.attrs.has_key("name"):
                        if singleinput.attrs.has_key("value"):
                            if singleinput.attrs.has_key("type") and singleinput.attrs["type"].lower()=="hidden":
                                formGeneratedUrl+= singleinput.attrs["name"]+"="+singleinput.attrs["value"]+"&"
                            else:
                                formGeneratedUrl += singleinput.attrs["name"]+"="+INPUT_SIGN+"&" #将给正常访问用户可控的input字段标上INPUT_SIGN
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
        #判断url是否已经在已访问列表或未访问列表存在
        if url in self.list_opt.get_unvisted() or url in self.list_opt.get_visited():
            return True
        else:
            if self.url_rewrite_type == "normal":
                query_string=urlparse.urlparse(url).query
                if query_string=='':
                    return False
                query_path=urlparse.urlparse(url).path
                query_raw_args=urlparse.parse_qs(query_string)
                query_args = dict([(k, v[0]) for k, v in query_raw_args.items()])
                same_path_args=self.list_opt.visited_url_args_map.get(query_path)
                if same_path_args==[{}] or same_path_args==None :#没有相同路径下的参数集
                    return False
                same_path_keys_list=[]
                [same_path_keys_list.append(one.keys()) for one in same_path_args]
                for same_path_key in same_path_keys_list:
                    if set(query_args.keys()) == set(same_path_key):#参数是否完全一致，若一致，则检查是否已有同类型的url
                        for query_key, query_value in query_args.items():
                            value_of_same_key = [single.get(query_key) for single in same_path_args if single.get(query_key) != None]#拿出所有带有相同key的非None的value
                            if len(list(set(value_of_same_key)))>=5:#若相同的参数在已访问列表中有超过5个以上不同的值，则认为相似
                                return True
                return False


    def evaluate_and_parse_url(self,url):
        if self.url_belong_to_host(url):
            if urlparse.urlparse(url).scheme == '':
                url=urlparse.urlparse(self.host).scheme+":"+url
            return url
        elif not re.match(r"^(\S+):", url):#排除伪协议及外部网站
            return urlparse.urljoin(self.host,url)
        else :return False

    def parse_form_path(self,formaction):
        #以//为开头的form action值 表示http/https
        if formaction.startswith("//"):
            schema=urlparse.urlparse(self.host)[0]
            url=schema+":"+formaction
            if self.url_belong_to_host(url):
                return url
            else:return False
         #以/为起始的form action值 表示在网站根目录
        elif formaction.startswith("/"):
            return urlparse.urljoin(self.host,formaction)
        #判断类似index.php的form action值
        else:
            parselist=urlparse.urlparse(self.list_opt.get_current_url())
            parsed_path=parselist.path
            if parselist.path.endswith("/"):
                parsed_path=parselist.path[:-1]
            path=os.path.split(parselist.path)[0]
            return urlparse.urljoin(self.host,path,formaction)

    def url_belong_to_host(self,url):
        parsed_list=urlparse.urlparse(url)
        if parsed_list.netloc==urlparse.urlparse(self.host).netloc:
            return True
        else:return False


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