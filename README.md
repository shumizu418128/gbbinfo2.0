このサイトの詳しい説明はこちら：
[GBBINFO-JPNの設計図](https://qiita.com/tari3210/items/0561e91774863d165af0)


```
.
└── 年度
    ├── top
    ├── rule
    ├── participants
    └── other content
└── others
    └── other content
```

### メモ
- 2023年のみ、ruleページと出場者データ未接続
- csvには出場者未定のシード権も記入
  - その際、出場者名は「～?/? 発表～」とする
  - 出身国が不明の場合、国コードは0とする
    - 国コード0はcountry.csvに追加済み
    - 国コード0の場合、world_mapには表示されない
