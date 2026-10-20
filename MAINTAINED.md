# 本仓怎么用（维护说明）

上游 `idootop/open-xiaoai` 已于 2026-04-04 归档，这里是我们自己的 fork。

- `main` / `v2`：**原样保留上游**，不要在上面改东西。
- **`bakey/live`：唯一维护分支**（本仓默认分支），设备上跑的二进制就是这个分支编出来的。

## 我们改了什么（相对上游，9 个提交 / 7 个文件）

| 文件 | 改动 | 为什么 |
|---|---|---|
| `packages/client-rust/src/services/audio/record.rs` | A113 S32→S16 **按通道缩放**：ch0–5 `>>8`、ch6/7 `>>13` | 原来所有通道统一 `>>8`，把播放参考通道削掉 33–78%；参考的满量程是 2^28，麦是 2^23 |
| `packages/client-rust/src/services/monitor/keys.rs` | 按键转发（175 行新增） | 原厂 4 个键的事件要送到服务端 |
| `.../monitor/playing.rs` | `mphelper mute_stat` 轮询 300 ms，状态按整数精确解析 | `contains("1")` 把任何带 1 的输出都当成"在播放" |
| `.../connect/data.rs` | 流帧 `bytes` 同时接受 JSON 数组和 base64 | 8ch/16k 的整数数组约 770 KB/s，base64 只有 1/4 体积 |
| `.../bin/client.rs` | `play` 失败打日志，不再 `let _ =` | 丢帧以前只有"句子被截断"这一个症状 |
| `.../monitor/kws.rs` `mod.rs` | 小改 | 配合上面 |

## 编译与部署

```bash
cd packages/client-rust
cross build --release --target armv7-unknown-linux-gnueabihf     # 首次约 16 s
md5 -q target/armv7-unknown-linux-gnueabihf/release/client
```

部署（`/data` 只有 13 MB，旧版推回 Mac，别在设备上留第二份）：

```bash
sshpass -e scp -O -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAuthentication=no \
  target/armv7-unknown-linux-gnueabihf/release/client root@<设备IP>:/tmp/client.new
ssh ... 'chmod +x /tmp/client.new && mv /tmp/client.new /data/open-xiaoai/client'
# 看门狗 30 s 内拉起；判据是 md5 三处一致：
#   /data/open-xiaoai/client == /proc/$(pidof client)/exe == 本地构建产物
```

## 当前部署记录

- 分支 `bakey/live` @ `ef94741`
- 二进制 md5：`d3909ee03062ae3ef7d348c4ac58c106`（本地构建 / 设备文件 / 运行进程三处一致，2026-10-20 12:51 核对）
- 回滚：设备上 `client.bak-20261020` = 上一版 `5092fd9d…`，`mv` 回去再 `kill $(pidof client)` 即可
- 设备：LX06 `192.168.5.5`，`/data/open-xiaoai/client-run.sh` 里带服务端 URL + ws token
