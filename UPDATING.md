# 这个仓库怎么更新

个人用的播客播放页，GitHub Pages 发布在 https://yw5aj.github.io/podcast/ 。

- `index.html`：播放器页面（播放、记进度、搜索、隐藏节目）。
- `shows.json`：节目和单集数据，页面只读这个文件。
- `update.py`：从小宇宙的公开网页读取最新单集，更新 `shows.json`。
- `.github/workflows/update.yml`：GitHub Actions 定时运行 `update.py`，每天两次
  （UTC 0:43 和 12:43）；`shows.json` 或脚本有改动被推送时也会跑一次。
- `update-log.txt`：最近一次运行的结果，每档节目一行。

## 规则

- 数据只从小宇宙自己的网页取（节目页 `/podcast/<id>` 和单集页 `/episode/<id>`）。
- 只记录标题、时长、日期、音频地址和封面地址。不下载、不保存任何音频或图片。
- 只增不减：已有的单集不会被删除。
- 访问要克制：每天两次，请求之间有间隔。

## 加一档新节目

在 `shows.json` 的 `shows` 末尾加一项，推送到 `main`：

```json
{ "id": "<节目id>", "title": "节目名", "episodes": [] }
```

节目 id 是小宇宙节目链接里 `/podcast/` 后面那 24 位字符。推送后 Actions 会自动运行，
一两分钟内把单集和封面补上。

## 出问题时

看 `update-log.txt`，或仓库的 Actions 页面里最近一次运行的输出。
如果某档节目显示“节目页读取失败”或“没找到单集”，多半是小宇宙改了页面结构或拦了访问，
需要改 `update.py` 里的解析。
