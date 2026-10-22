# launchd와 cron으로 분석 작업 예약 실행

> 매일 아침 리포트를 뽑는 스크립트는 리눅스에선 cron, 맥에선 launchd로 돌린다. 예약보다 어려운 것은 "놓쳤을 때"와 "두 번 돌았을 때"다.

## cron (리눅스)

`crontab -e`로 편집한다. 한 줄이 작업 하나다.

```
# 분 시 일 월 요일  명령
30 7 * * 1-5  cd /home/me/report && /usr/bin/python3 run.py >> /home/me/report/logs/run.log 2>&1
```

- 평일 07:30에 실행한다.
- cron은 로그인 셸이 아니다. `PATH`가 짧아서 `python3`를 못 찾는 일이 흔하다. 절대 경로를 쓴다.
- 출력을 리다이렉트하지 않으면 메일로 가거나 버려진다. `>> 파일 2>&1`로 남긴다.
- cron 자체의 실행 기록은 배포판마다 다르다. `grep CRON /var/log/syslog` 또는 `journalctl -u cron`.
- 꺼져 있던 시각의 작업은 실행하지 않는다. 놓친 실행을 챙기려면 `anacron`이나 systemd timer의 `Persistent=true`를 쓴다.

## launchd (맥)

맥에도 cron이 있지만 권장 방식은 launchd다. 작업 하나를 plist 파일 하나로 정의한다.

- 내 계정 작업: `~/Library/LaunchAgents/` (로그인해 있을 때 돈다)
- 시스템 전체 작업: `/Library/LaunchDaemons/` (root, 로그인 없이)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>local.report.daily</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/Users/me/report/run.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/me/report</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>7</integer>
        <key>Minute</key>
        <integer>30</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>/Users/me/report/logs/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/me/report/logs/stderr.log</string>
</dict>
</plist>
```

등록과 확인:

```
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.report.daily.plist
launchctl print gui/$(id -u)/local.report.daily     # 상태, 마지막 종료 코드
launchctl kickstart gui/$(id -u)/local.report.daily # 지금 한 번 실행
launchctl bootout gui/$(id -u)/local.report.daily   # 내리기
```

- `ProgramArguments`는 셸을 거치지 않는다. `~`, `>>`, `&&`가 동작하지 않는다. 필요하면 셸 스크립트를 따로 두고 그것을 부른다.
- 로그는 `StandardOutPath`, `StandardErrorPath`에 지정한 곳에 쌓인다. 지정하지 않으면 사라진다.
- launchd 자체 기록은 `log show --predicate 'subsystem == "com.apple.xpc.launchd"' --last 1h`로 본다.
- plist를 고친 뒤에는 bootout 후 다시 bootstrap 해야 반영된다.

## 잠자기와 놓친 실행

| 상황 | cron | launchd (`StartCalendarInterval`) |
|---|---|---|
| 예약 시각에 잠자기 상태 | 실행 안 함 | 깨어난 직후 한 번 실행 |
| 여러 번 놓침 (며칠 잠자기) | 실행 안 함 | 몇 번을 놓쳤든 한 번만 실행 |
| 예약 시각에 전원 꺼짐 | 실행 안 함 | 실행 안 함 |

launchd의 "깨어나서 한 번"은 편하지만 함정이 있다. 07:30 작업이 11:00에 돌 수 있고, 사흘 치를 놓쳐도 하루 치만 돈다. 그래서 스크립트가 "오늘 날짜"를 기준으로 계산하면 빠진 날이 생긴다. 실행 시각이 아니라 "마지막으로 성공한 날짜 다음부터 어제까지"를 처리하게 만든다.

`StartInterval`(N초마다)은 잠자기 동안의 실행을 쌓지 않는다. 노트북에서 정해진 시각 작업을 꼭 돌려야 한다면 `pmset repeat wake`로 그 전에 깨우는 방법도 있다.

## 멱등성 체크리스트

같은 날짜로 두 번 돌려도 결과가 같아야 한다. 놓친 실행 보충, 수동 재실행, 중복 예약이 모두 "두 번 돌기"를 만든다.

- [ ] 처리 대상 날짜를 인자로 받는다 (`run.py --date 2026-10-19`). 기본값만 "어제"로 둔다
- [ ] 결과 쓰기가 덮어쓰기다. `INSERT`로 쌓지 않고 그 날짜 파티션을 지우고 다시 쓴다 (`DELETE WHERE dt = ?` 후 `INSERT`, 또는 `INSERT OVERWRITE`)
- [ ] 파일 출력은 임시 파일에 쓰고 마지막에 이름을 바꾼다. 중간에 죽어도 반쪽 파일이 남지 않는다
- [ ] 메일, 메신저 알림 같은 외부 부작용은 "이 날짜로 이미 보냈나"를 기록하고 확인한다
- [ ] 동시에 두 개가 뜨지 않게 잠금 파일을 둔다 (`flock`, 또는 시작 시 pid 파일 확인)
- [ ] 마지막 성공 날짜를 기록하고, 다음 실행은 그 다음 날부터 어제까지 빈 날을 모두 처리한다
- [ ] 실패하면 0이 아닌 종료 코드로 끝난다. 예외를 삼키고 0으로 끝내면 스케줄러는 성공으로 안다
- [ ] 같은 날짜를 두 번 돌려 결과 파일의 해시나 행 수가 같은지 한 번은 직접 확인했다
