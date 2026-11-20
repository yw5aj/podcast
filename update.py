#!/usr/bin/env python3
"""更新 shows.json：从小宇宙的公开网页读取每档节目的最新单集。

只读取 xiaoyuzhoufm.com 的节目页和单集页，只记录标题、时长、日期、音频地址和封面地址，
不下载任何音频或图片。只增不减：已有的单集不会被删除。
运行结果写在 update-log.txt 里，方便排查。
"""
import datetime
import html
import json
import re
import sys
import time
import urllib.request

BASE = "https://www.xiaoyuzhoufm.com"
UA = ("Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Mobile Safari/537.36")
MAX_EPISODE_FETCHES = 80
PAUSE = 1.5  # 两次请求之间的间隔（秒）

ID_RE = re.compile(r"^[0-9a-f]{24}$")
AUDIO_RE = re.compile(r"https://media\.xyzcdn\.net/[A-Za-z0-9_\-./]+?\.(?:m4a|mp3)")
NEXT_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
EP_LINK_RE = re.compile(r"/episode/([0-9a-f]{24})")

fetches = 0


def get(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def next_data(page):
    m = NEXT_RE.search(page)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except ValueError:
        return None


def walk(node):
    """遍历 JSON，产出所有字典。"""
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v)


def audio_of(d):
    for path in (("enclosure", "url"), ("media", "source", "url"), ("mediaKey",)):
        v = d
        for k in path:
            v = v.get(k) if isinstance(v, dict) else None
        if isinstance(v, str) and AUDIO_RE.fullmatch(v):
            return v
    return None


def date_of(s):
    """ISO 时间 -> 北京时间的 YYYY-MM-DD。"""
    if not isinstance(s, str):
        return None
    try:
        t = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return s[:10] if re.match(r"\d{4}-\d{2}-\d{2}", s) else None
    if t.tzinfo is None:
        t = t.replace(tzinfo=datetime.timezone.utc)
    return t.astimezone(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d")


def episode_from_dict(d):
    eid = d.get("eid")
    if not (isinstance(eid, str) and ID_RE.match(eid) and isinstance(d.get("title"), str)):
        return None
    ep = {"id": eid, "title": d["title"].strip()}
    dur = d.get("duration")
    if isinstance(dur, (int, float)) and dur > 0:
        ep["min"] = max(1, round(dur / 60))
    dt = date_of(d.get("pubDate"))
    if dt:
        ep["date"] = dt
    au = audio_of(d)
    if au:
        ep["audio"] = au
    return ep


def cover_from(data, page, pid):
    if data:
        for d in walk(data):
            if d.get("pid") == pid and isinstance(d.get("image"), dict):
                img = d["image"]
                for k in ("smallPicUrl", "middlePicUrl", "picUrl", "largePicUrl"):
                    if isinstance(img.get(k), str) and img[k].startswith("https://"):
                        return img[k]
    m = re.search(r'<meta[^>]+property="og:image"[^>]+content="(https://[^"]+)"', page)
    return html.unescape(m.group(1)) if m else None


def parse_show(page, pid):
    """返回 (单集列表[从新到旧], 封面地址)。"""
    data = next_data(page)
    eps, seen = [], set()
    if data:
        for d in walk(data):
            ep = episode_from_dict(d)
            if ep and ep["id"] not in seen:
                seen.add(ep["id"])
                eps.append(ep)
    if not eps:  # 页面结构变了时的退路：只拿到单集 id，其余去单集页补
        for eid in EP_LINK_RE.findall(page):
            if eid not in seen:
                seen.add(eid)
                eps.append({"id": eid})
    if all("date" in e for e in eps):
        eps.sort(key=lambda e: e["date"], reverse=True)
    return eps, cover_from(data, page, pid)


def parse_episode(page, eid):
    out = {}
    data = next_data(page)
    if data:
        for d in walk(data):
            if d.get("eid") == eid:
                out = episode_from_dict(d) or {}
                break
    if "audio" not in out:
        m = AUDIO_RE.search(page)
        if m:
            out["audio"] = m.group(0)
    if "title" not in out:
        m = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', page)
        if m:
            out["title"] = html.unescape(m.group(1)).strip()
    if "date" not in out:
        m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', page)
        if m and date_of(m.group(1)):
            out["date"] = date_of(m.group(1))
    if "min" not in out:
        m = re.search(r'"timeRequired"\s*:\s*"PT(\d+)M"', page)
        if m:
            out["min"] = int(m.group(1))
    return out


def fill_from_episode_page(ep):
    """读单集页，把缺的字段补上。返回是否有变化。"""
    global fetches
    if fetches >= MAX_EPISODE_FETCHES:
        return False
    fetches += 1
    time.sleep(PAUSE)
    got = parse_episode(get(f"{BASE}/episode/{ep['id']}"), ep["id"])
    changed = False
    for k in ("title", "min", "date", "audio"):
        if got.get(k) and not ep.get(k):
            ep[k] = got[k]
            changed = True
    return changed


def update_show(show, log):
    pid = show["id"]
    try:
        page = get(f"{BASE}/podcast/{pid}")
    except Exception as e:  # noqa: BLE001
        log.append(f"{show['title']}: 节目页读取失败（{e}）")
        return False
    listed, cover = parse_show(page, pid)
    if not listed:
        log.append(f"{show['title']}: 节目页里没找到单集（页面结构可能变了）")
        return False
    changed = False
    if cover and show.get("cover") != cover:
        show["cover"] = cover
        changed = True

    have = {e["id"]: e for e in show["episodes"]}
    new = []
    for ep in listed:
        old = have.get(ep["id"])
        if old is None:
            new.append(ep)
        else:  # 已有的单集：以节目页上的数据为准（补缺，也纠正抄错的地址）
            for k in ("title", "min", "date", "audio"):
                if ep.get(k) and old.get(k) != ep[k]:
                    old[k] = ep[k]
                    changed = True
    if new:
        show["episodes"] = new + show["episodes"]
        changed = True

    errors = 0
    for ep in show["episodes"]:
        if ep.get("audio") and ep.get("title") and ep.get("min"):
            continue
        try:
            if fill_from_episode_page(ep):
                changed = True
        except Exception:  # noqa: BLE001
            errors += 1
    for ep in show["episodes"]:
        ep.setdefault("title", "（标题待补）")
        ep.setdefault("min", 0)
        ep.setdefault("audio", None)

    ok = sum(1 for e in show["episodes"] if e.get("audio"))
    note = f"{show['title']}: 可播放 {ok}/{len(show['episodes'])} 集"
    if new:
        note += f"，新增 {len(new)} 集"
    if errors:
        note += f"，{errors} 个单集页读取失败"
    log.append(note)
    return changed


def main():
    with open("shows.json", encoding="utf-8") as f:
        data = json.load(f)
    before = json.dumps(data, ensure_ascii=False, sort_keys=True)
    log = []
    for show in data["shows"]:
        update_show(show, log)
        time.sleep(PAUSE)

    ids = [e["id"] for s in data["shows"] for e in s["episodes"]]
    if len(ids) != len(set(ids)) or not all(ID_RE.match(i) for i in ids):
        log.append("校验失败：单集 id 重复或格式不对，这次不写入。")
        changed = False
    else:
        changed = json.dumps(data, ensure_ascii=False, sort_keys=True) != before
        if changed:
            data["updated"] = datetime.datetime.now(
                datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d")
            with open("shows.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
                f.write("\n")
    with open("update-log.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(log) + "\n")
    print("\n".join(log))
    print("shows.json 有更新" if changed else "shows.json 没有变化")
    return 0


if __name__ == "__main__":
    sys.exit(main())
