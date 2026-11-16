# FOFA 字段与运算符速查

## 运算符

| 运算 | 含义 | 示例 |
|------|------|------|
| `=` | 匹配（含模糊语义视字段） | `title="login"` |
| `==` | 精确匹配 | `server=="Apache"` |
| `!=` | 不匹配 | `country!="CN"` |
| `*=` | 模糊匹配 | `host*="vpn"` |
| `&&` / `\|\|` | 且 / 或 | `port="80" \|\| port="443"` |
| `()` | 分组 | `(a \|\| b) && c` |

## 常用字段

| 字段 | 含义 |
|------|------|
| `ip` | IP / CIDR |
| `port` | 端口 0–65535 |
| `protocol` | 协议（ssh/ftp/snmp/socks5 等） |
| `base_protocol` | 传输层 tcp/udp |
| `host` | 主机名 / 访问地址 |
| `domain` | 主域 |
| `title` | 网页标题 |
| `body` | 正文 |
| `header` | 响应头 |
| `banner` | Banner / 服务响应原文 |
| `server` | Server 头 |
| `status_code` | HTTP 状态码 |
| `country` | 国家代码（如 CN/US/JP） |
| `region` | 省/州 |
| `city` | 城市 |
| `asn` | ASN 号 |
| `org` | 网络组织 |
| `os` | 操作系统 |
| `app` | 应用识别名 |
| `product` / `product.version` / `product_category` | 产品相关 |
| `cloud_name` / `is_cloud` | 云厂商 |
| `cert` / `cert.subject` / `cert.subject.cn` / `cert.subject.org` | 证书持有者 |
| `cert.issuer` / `cert.issuer.cn` / `cert.issuer.org` | 证书颁发者 |
| `cert.sn` / `cert.domain` / `cert.is_valid` / `cert.is_match` / `cert.is_equal` | 证书其它 |
| `tls.version` / `tls.ja3s` / `jarm` | TLS 指纹 |
| `icon_hash` / `fid` / `header_hash` / `body_hash` / `banner_hash` / `banner_fid` | 哈希指纹 |
| `is_domain` / `is_ipv6` / `is_honeypot` / `is_fraud` | 布尔资产属性 |
| `cname` / `cname_domain` | CNAME |
| `after` / `before` | 更新时间窗口 |
| `cert.after` / `cert.before` | 证书时间 |

## 不可转换固定文案

```text
该需求不能直接转换为FOFA搜索语句
```
