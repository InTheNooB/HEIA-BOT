#!/usr/bin/env python3
import argparse
import json
import sys
import time
from urllib.parse import quote, urljoin
from xml.etree import ElementTree as ET

import requests

NS = {
    "d": "DAV:",
    "nc": "http://nextcloud.org/ns",
}

PROP_REQUEST_BODY = """<?xml version="1.0" encoding="utf-8" ?>
<d:propfind xmlns:d="DAV:" xmlns:nc="http://nextcloud.org/ns">
  <d:prop>
    <d:resourcetype/>
    <d:getcontentlength/>
    <d:getlastmodified/>
    <d:getcontenttype/>
  </d:prop>
</d:propfind>""".strip()


class Crawler:
    def __init__(
        self, base, token, password=None, timeout=30, max_retries=3, backoff=0.8
    ):
        # Nextcloud public WebDAV endpoints
        self.webdav_root = urljoin(base.rstrip("/") + "/", "public.php/webdav/")
        # Some deployments prefer /public.php/dav/files/{token}/ — we’ll try that if the first probe fails
        self.alt_root_template = urljoin(
            base.rstrip("/") + "/", f"public.php/dav/files/{token}/"
        )
        self.session = requests.Session()
        # For most installations: user=token, pass=(empty or share password)
        self.session.auth = (token, password or "")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff
        self.base_share_url = urljoin(base.rstrip("/") + "/", f"index.php/s/{token}/")

        # Detect which endpoint works
        print(f"Debug: Trying WebDAV root: {self.webdav_root}")
        if not self._probe(self.webdav_root):
            print(
                f"Debug: {self.webdav_root} did not work, trying alternative root: {self.alt_root_template}"
            )
            if self._probe(self.alt_root_template):
                self.webdav_root = self.alt_root_template
                print(f"Debug: Using alternative WebDAV root: {self.webdav_root}")
            else:
                print("Debug: Neither endpoint worked.")
                raise RuntimeError(
                    "Unable to access public WebDAV. "
                    "Check token/password or server availability."
                )
        else:
            print(f"Debug: Using WebDAV root: {self.webdav_root}")

    def _probe(self, url):
        print(f"Debug: Probing {url}")
        try:
            r = self.session.request(
                "PROPFIND",
                url,
                headers={"Depth": "0"},
                data=PROP_REQUEST_BODY,
                timeout=self.timeout,
            )
            print(f"Debug: Probe status code: {r.status_code}")
            return r.status_code in (207, 301, 302)
        except requests.RequestException as e:
            print(f"Debug: Probe exception: {e}")
            return False

    def _propfind(self, href, depth="1"):
        # Robust PROPFIND with basic retry
        last_exc = None
        for attempt in range(1, self.max_retries + 1):
            try:
                print(f"Debug: PROPFIND {href} (attempt {attempt}, depth {depth})")
                r = self.session.request(
                    "PROPFIND",
                    href,
                    headers={"Depth": depth},
                    data=PROP_REQUEST_BODY,
                    timeout=self.timeout,
                )
                print(f"Debug: PROPFIND status code {r.status_code}")
                if r.status_code not in (207,):
                    # Some servers redirect without auth headers on first go; follow and retry once
                    if r.is_redirect or r.status_code in (301, 302, 303, 307, 308):
                        print(f"Debug: Redirected to {r.headers.get('Location', href)}")
                        href = r.headers.get("Location", href)
                        continue
                    r.raise_for_status()
                return r.text
            except requests.RequestException as e:
                print(
                    f"Debug: PROPFIND exception: {e}, sleeping for {self.backoff * attempt} seconds"
                )
                last_exc = e
                time.sleep(self.backoff * attempt)
        print(f"Debug: All PROPFIND attempts failed")
        raise last_exc

    @staticmethod
    def _is_collection(prop_elem):
        rt = prop_elem.find("d:resourcetype", NS)
        return rt is not None and rt.find("d:collection", NS) is not None

    def _normalize_child_href(self, href):
        # Normalize to a path relative to root
        if not href.startswith(self.webdav_root):
            # Some servers return absolute paths; make them absolute and then slice
            if href.startswith("/"):
                # Rebuild absolute and continue
                href = urljoin(self.webdav_root, href.lstrip("/"))
        return href

    def _browser_url_for_file(self, path):
        """
        Build a click-ready browser URL for a file within the public share:

        https://.../index.php/s/{token}/download?path=/PARENT&files=FILENAME
        """
        # path is like 'Dir/Subdir/file.pdf'
        parts = path.strip("/").split("/")
        if len(parts) == 1:
            parent = "/"
            fname = parts[0]
        else:
            parent = "/" + "/".join(parts[:-1])
            fname = parts[-1]
        return (
            self.base_share_url
            + "download"
            + "?path="
            + quote(parent, safe="/")
            + "&files="
            + quote(fname)
        )

    def _node_from_prop(self, root_href, response_elem):
        href = response_elem.findtext("d:href", default="", namespaces=NS)
        if not href:
            return None

        href = self._normalize_child_href(urljoin(root_href, href))
        # Convert to a display path relative to webdav_root
        rel = href[len(self.webdav_root) :].strip("/")
        prop = response_elem.find(".//d:prop", NS)
        if prop is None:
            return None

        is_dir = self._is_collection(prop)
        size = prop.findtext("d:getcontentlength", default="", namespaces=NS)
        mtime = prop.findtext("d:getlastmodified", default="", namespaces=NS)
        ctype = prop.findtext("d:getcontenttype", default="", namespaces=NS)

        name = rel.split("/")[-1] if rel else ""  # root comes back too; filter later

        node = {
            "name": name,
            "path": rel,  # path relative to the share root
            "type": "directory" if is_dir else "file",
            "size": int(size) if size.isdigit() else None,
            "last_modified": mtime or None,
            "content_type": ctype or None,
        }
        if not is_dir and rel:
            node["web_url"] = self._browser_url_for_file(rel)
        print(f"Debug: Parsed node: {node}")
        return node

    def list_dir(self, href):
        print(f"Debug: Listing directory {href}")
        xml_text = self._propfind(href, depth="1")
        root = ET.fromstring(xml_text)
        items = []
        for resp in root.findall("d:response", NS):
            node = self._node_from_prop(href, resp)
            if not node:
                continue
            # Skip the collection itself (Depth:1 returns the queried folder as first item)
            if (
                node["path"] == ""
                or href.rstrip("/") == self.webdav_root.rstrip("/")
                and node["name"] == ""
            ):
                continue
            items.append(node)
        print(f"Debug: list_dir found {len(items)} items in {href}")
        return items

    def crawl(self):
        visited = set()

        def walk(href):
            rel = href[len(self.webdav_root) :].strip("/")
            if rel in visited:
                return []  # prevent infinite recursion
            visited.add(rel)

            children = self.list_dir(href)
            result_children = []
            for child in children:
                if child["type"] == "directory":
                    sub_href = urljoin(self.webdav_root, child["path"] + "/")
                    child["children"] = walk(sub_href)
                result_children.append(child)
            return result_children

        return {
            "type": "directory",
            "name": "",
            "path": "",
            "children": walk(self.webdav_root),
        }


def main():
    ap = argparse.ArgumentParser(
        description="Recursively crawl a Nextcloud public share over WebDAV and emit JSON."
    )
    ap.add_argument(
        "--base", required=True, help="Base URL, e.g. https://drive.switch.ch"
    )
    ap.add_argument(
        "--token", required=True, help="Public share token from the /s/<token> link"
    )
    ap.add_argument(
        "--password",
        default=None,
        help="Share password if the link is password-protected",
    )
    ap.add_argument("--out", default="tree.json", help="Output JSON file")
    args = ap.parse_args()

    try:
        print(
            f"Debug: Starting crawl with base={args.base}, token={args.token}, password={args.password}"
        )
        crawler = Crawler(args.base, args.token, password=args.password)
        tree = crawler.crawl()
        print("Debug: Writing output JSON")
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(tree, f, ensure_ascii=False, indent=2)
        print(f"Wrote {args.out}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
