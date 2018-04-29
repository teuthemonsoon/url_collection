# url_collection
编写web渗透工具的基石<br>
<br>
使用`基于广度`的搜索算法爬取url，默认最大深度为`5`<br>
可从
`<a href=${url}>`
及从form表单中提取url并自动拼接参数<br>
## 用法
python url_collection.py https://www.github.com

## todo
将增加对url相似度的识别<br>
将增加在js中提取url<br>
将增加对本域名及其子域的url搜集<br>
