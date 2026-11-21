# 这个仓库怎么更新

个人用的播客播放页，GitHub Pages 发布在 https://yw5aj.github.io/podcast/ 。

- `index.html`：播放器页面（播放、记进度、搜索、隐藏节目）。
- `shows.json`：节目和单集数据，页面只读这个文件。
- `update.py`：读取每档节目的最新单集，更新 `shows.json`。小宇宙独家的节目读它的公开网页，
  其余节目读标准 RSS。
- `.github/workflows/update.yml`：GitHub Actions 定时运行 `update.py`，每天四次
  （UTC 1:23、7:23、13:23、19:23；GitHub 的定时偶尔会漏，多排几次保险）；`shows.json` 或脚本有改动被推送时也会跑一次。
- `update-log.txt`：最近一次运行的结果，每档节目一行。

## 规则

- 小宇宙的节目只从小宇宙自己的网页取（节目页 `/podcast/<id>` 和单集页 `/episode/<id>`）；
  RSS 节目只读它自己的 feed（查 feed 地址时会问一次 Apple 播客目录）。
- 只记录标题、时长、日期、音频地址和封面地址。不下载、不保存任何音频或图片。
- 只增不减：已有的单集不会被删除。
- 访问要克制：每天四次，每次每档节目只读一个页面，请求之间有间隔。

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

## 加一档有标准 RSS 的节目

```json
{ "id": "<任意 24 位十六进制，定了就别改>", "title": "节目名", "find": "节目名", "country": "cn", "episodes": [] }
```

- `find` 是节目在 Apple 播客里的名字，脚本会查出 RSS 地址并写进 `feed`；已经知道地址就直接写 `feed`。
- 同名节目多时加 `"by": "主播或机构名"` 来区分。
- 第一次导入最近 200 集，之后只加新出的。
- 如果日志里写“RSS 读取失败”，多半是小宇宙托管的 feed（`feed.xyzfm.space`），它拦服务器访问。
  这种节目改用上面的小宇宙方式：`id` 换成小宇宙的节目 id，去掉 `find` 和 `feed`。

## 定时不触发时

GitHub 把“最后修改定时设置的人”当作定时运行的发起人，这个人必须是对仓库有写权限的账号。
所以 `.github/workflows/update.yml` 里的 `schedule` 一段，必须用仓库主人（yw5aj）的署名提交；
用别的署名提交后，手动和推送触发都正常，唯独定时不会跑。
新仓库的定时有时还要先手动运行一次（Actions 页的 Run workflow）才会激活。
