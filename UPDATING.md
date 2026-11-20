# 如何更新 shows.json

这个仓库是一个个人用的播客播放页（GitHub Pages：https://yw5aj.github.io/podcast/）。
`index.html` 负责播放和记进度，节目数据全部在 `shows.json` 里。更新节目 = 只改 `shows.json`。

## 规则

- 数据只从小宇宙自己的网页取：`https://www.xiaoyuzhoufm.com/podcast/<节目id>` 和
  `https://www.xiaoyuzhoufm.com/episode/<单集id>`。不要用其他网站。
- 只记录标题、时长、日期和音频地址。**不要下载、保存或上传任何音频文件。**
- 访问要克制：每天一次；单集页面一次最多同时抓 6 个，分批顺序进行；
  遇到限流就等一下、逐个重试一次，仍失败就留到下次。
- 每次运行最多抓 60 个单集页面，剩下的留给下一次。
- 只增不减：`shows.json` 里已有的单集永远不删、不改 id。

## shows.json 结构

```json
{
  "updated": "YYYY-MM-DD",
  "shows": [
    { "id": "<24位十六进制节目id>", "title": "节目名",
      "episodes": [
        { "id": "<24位十六进制单集id>", "title": "标题", "min": 112,
          "date": "YYYY-MM-DD", "audio": "https://media.xyzcdn.net/....m4a" }
      ] }
  ]
}
```

- `episodes` 按从新到旧排列。
- `audio` 可以是 `null`（表示还没抓到），页面会暂时不显示这一集。
- `date` 可以缺省；能从单集页面拿到发布日期就补上。

## 每次更新的步骤

1. 对 `shows.json` 里的每档节目，打开它的节目页，读出页面上列出的单集
   （id、标题、时长分钟数），顺序为从新到旧。节目页只公开最新约 15 集，这是正常的。
2. 找出两类需要处理的单集：
   - 节目页上有、`shows.json` 里没有的（新单集，或 `episodes` 为空的新节目）；
   - `shows.json` 里已有但 `audio` 为 `null` 的。
3. 逐个打开这些单集的页面，取出：
   - 音频直链：以 `https://media.xyzcdn.net/` 开头、以 `.m4a` 或 `.mp3` 结尾；
   - 发布日期（`YYYY-MM-DD`），拿不到就不写。
4. 校验后再写入：
   - id 必须是 24 位、只含 `0-9a-f`；不符合就重新读一次节目页确认，不要猜；
   - 音频地址不符合上面的格式，就把 `audio` 记为 `null`；
   - 同一个 id 不能出现两次。
5. 把新单集插到对应节目 `episodes` 的最前面，保持从新到旧；更新顶层的 `updated` 为当天日期。
6. 用 `python3 -m json.tool shows.json > /dev/null` 确认文件是合法 JSON。
7. 有变化才提交：直接提交到 `main` 并推送（Pages 从 `main` 发布）。
   提交说明写清加了哪些节目的几集。没有变化就什么都不做。

## 加一档新节目

在 `shows` 末尾加一项：`{"id": "<节目id>", "title": "节目名", "episodes": []}`，
然后按上面的步骤运行一次。节目 id 是小宇宙节目链接里 `/podcast/` 后面那一串。
