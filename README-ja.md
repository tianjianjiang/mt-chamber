# Multi-thread chamber
マルチスレッドでパイプライン処理を行うためのフレームワーク

イントロ
=======================================================
このソフトウェアは、専用のスクリプト「ChamberLang」を利用することで、テキストやオブジェクト列に対してパイプライン処理をマルチスレッドで行うことをサポートします。
まず、簡単な例を見てみましょう。

    Read:file="./input" > inputdata
    Write:file="./output" < inputdata

このコードを``./example-code`` の名前で保存しておきます。
また、適当な行数を持ったテキストファイル ``./input`` も用意しておきましょう。
プログラムを実行するには

    $ mt-chamber.py --threads 2 ./example-code

これを実行すると、 ``./input`` と同一の内容の ``./output`` が生成されます。

このスクリプトは以下の解釈ができます。

1. ``Read`` コマンドによって ``./input`` の内容を一行ずつ読み込み、変数 ``inputdata`` に出力する。
2. ``Write`` コマンドによって ``inputdata`` の内容を一行ずつ ``./output`` に書き出す。

ここで注意すべきことは、 ``Read`` が完全に終了してから ``Write`` が始まるわけではないことです。
``Read`` はファイルを一行読み込むと、その内容を直ちに ``Write`` に渡します。

``mt-chamber.py`` では、以下の引数を指定できます。

* ``--threads``: スレッド数。
* ``--unsrt-limit``: プロセス間のデータの受け渡しに用いられるキューのサイズに影響します。この値は ``--threads`` に比べて十分大きくしておくべきです。
* ``--prompt``: プロンプトモード。スクリプトの実行中に対話画面を表示し、進捗状況の確認やデバッグを行います。
* ``FILE``: 実行するスクリプト。指定されなかった場合は標準入力を読み込みます。``--prompt`` が指定された場合は標準入力はプロンプト用に使用されるため、``FILE`` を指定する必要があります。

ChamberLang
=======================================================

ChamberLang の基本
-------------------------------------------------------

ChamberLang の一行は、基本的にコマンド、コマンドのオプション、入力、出力から成っています。
行の末尾にバックスラッシュ ``\`` がある場合、その行は次の行とスペースを挟んで連結されます。
また、行に ``#`` が含まれる場合、``#`` 以降の文字列はコメントとして扱われます。

    コマンド:オプション:オプション... < 入力 > 出力

入力や出力は一般的なシェルのようにコマンドに対して1個である必要はありません。コマンドによっては複数の入出力を受ける場合もあります。
入出力変数として利用可能な文字列は、英数字とアンダースコアのみであり、数字から始まってはいけません。

オプションは ``オプション名=値`` の形式で記述し、複数のオプションを指定する場合は ``:`` で区切ります。
オプション名のみを記述した場合は、自動的に ``オプション名=True`` として解釈されます。
オプションの値に空白を含む文字列を指定する場合は、それらの文字列を ``" "`` で囲みます。

``plugins`` に含まれる ``LengthCleaner`` コマンドを利用する例を以下に示します。

    # ファイルを読み込む
    Read:file="./en.tok" > en_tok
    Read:file="./ja.tok" > ja_tok
    # 単語数でクリーニング
    LengthCleaner:maxlen1=80:maxlen2=80 < en_tok ja_tok > en_clean ja_clean
    # ファイルを書き出す
    Write:file="./en.clean" < en_clean
    Write:file="./ja.clean" < ja_clean

この例では、行ごとに対応した2つのファイル ``./en.tok`` と ``./ja.tok`` を読み込み、各行の単語数が80より多ければ、両方のファイルから該当する行を除去します。

各コマンドのスレッド数を個別に指定したい場合は ``*`` を使います。

    # 次のコマンドだけ --threads 引数の内容にかかわらず 3 スレッドで実行
    LengthCleaner *3 < en_tok ja_tok > en_clean ja_clean


エイリアス
-------------------------------------------------------

オプションが長くなる場合、それをスクリプトの中に書いてしまうと可読性が低くなります。
その問題を回避するために、ChamberLang には ``Alias`` と呼ばれるコマンドがあります。
Alias を利用することで、長いコマンドを別の名前で置き換えることができます。

    Alias MyCleaner LengthCleaner:maxlen1=80,maxlen2=80
    MyCleaner < en_tok ja_tok > en_clean ja_clean

Alias は C の ``#define`` によく似ています。定義されたすべての別名は、スクリプトの解釈前に置換されます（プリプロセス）。


より複雑な書き方
-------------------------------------------------------

コマンドに対する入出力を指定する際、それぞれの入出力を複数の ``<`` や ``>`` によって分割して指定できます。
例えば

    LengthCleaner:maxlen1=80:maxlen2=80 < en_tok ja_tok > en_clean ja_clean

を書き換えると

    LengthCleaner:maxlen1=80:maxlen2=80 < en_tok < ja_tok > en_clean ja_clean

更に、オプションの位置はコマンドの直後である必要は無いため

    LengthCleaner:maxlen1=80 < en_tok :maxlen2=80 < ja_tok > en_clean ja_clean

読むのが難しくなりました。では、Alias の #define とよく似た機能を活用してみましょう。

    Alias MyCleaner LengthCleaner:maxlen1=80 < en_tok 
    MyCleaner:maxlen2=80 < ja_tok > en_clean_with_ja ja_clean
    MyCleaner:maxlen2=70 < zh_tok > en_clean_with_zh zh_clean

何をしたか分かりましたか？
この例では、 ``Alias`` を使うことでスクリプトの一部 ``LengthCleaner:maxlen1=80 < en_tok`` を置き換えました。これにより、1つ目の入力とオプションだけは固定し、残りのオプションと入力を自由に変えられる「コマンドのようなもの」を定義したことになります。


利用可能なコマンド
=======================================================

[コマンドリファレンス](CommandReference.md)を参照してください。


Pythonを使ったコマンドの定義
=======================================================

では、Pythonを使ったより柔軟なコマンドの定義方法を見て行きましょう。

新しいコマンドを定義するには、 ``plugins`` 下にPythonのファイルを設置します。
まず、コマンドを定義するためのファイルを ``plugins/コマンド.py`` に設置します。
このファイルでは、以下のような ``Command`` クラスを定義します。

```python
class Command:

    # 設定変数
    InputSize = 1
    OutputSize = 1
    MultiThreadable = True
    ShareResources = False

    def __init__(self, options...):
        ::::

    def routine(self, instream):
        ::::

    def hook_prompt(self, statement, lock):
        ::::

    def kill(self):
        ::::

    def __del__(self):
        ::::
```

設定変数の意味は次のとおりです。

* **InputSize:** 入力タプルのサイズ。
* **OutputSize:** 出力タプルのサイズ。
* **MultiThreadable:** コマンドを並列処理できる場合は ``True`` にします。ファイルの読み書きのように、マルチスレッド化が困難な場合は ``False`` に設定します。
* **ShareResources:** リソースをスレッド間で共有する場合は ``True`` にします。この場合、スレッド間で変数の使い回しが可能になります。それぞれのスレッドでリソースを独立させたい場合は ``False`` に設定します。

``Command`` クラスでは、最低限 ``routine`` 関数を定義します。また、必要に応じて ``__init__`` 関数や ``__del__`` 関数を定義します。

* ``__init__``: ``Command`` クラスのインスタンスが生成された際に呼び出されます。``Command`` クラスのインスタンスは、``MultiThreadable`` と ``ShareResources`` の内容に従って、決まった個数が生成されます。``MultiThreadable`` が ``False`` または ``ShareResources`` が ``True`` の場合は1個だけ生成され、それ以外の場合は指定されたスレッド数の分だけ生成されます。
引数 ``options...`` では、コマンドのオプションを一般的な関数の引数として定義します。
* ``routine``: コマンドがデータを受け取った際に呼び出されます。 ``instream`` 引数には入力データがタプルとして格納されます。処理が終わったら出力データをタプルとして返します。タプルの代わりに ``None`` を返した場合、コマンドを終了し、以降のコマンドも連鎖的に終了します。
* ``hook_prompt``: プロンプトモードでコマンドが入力された際に実行されます。引数 ``statement`` には空白で分割されたコマンドと引数のリストが与えられます。 ``lock`` は mt-chamber の全スレッド間で共有される排他的ロックであり、標準出力などに結果を表示する際に利用します。
* ``kill``: プロンプトで ``kill`` コマンドが実行された際に呼び出されます。スクリプトが終了に向かう際、``routine`` 内でプログラムがブロックされているなどの原因で終了処理が正しく行われない場合があります。``kill`` では、正常な終了のために必要な処理を記述します。
* ``__del__``: スクリプトが終了した段階で呼び出されます。

``InputSize`` と ``OutputSize`` は定数の代わりに関数として定義することも出来ます。

```python
class Command:

    def InputSize(self, size):
        ::::
            raise Exception(...)
        ::::

    ::::
```

関数として定義する場合は、実際にスクリプト中で与えられた入出力の数 ``size`` を引数として取ります。
与えられた ``size`` に問題がなければ関数を正常終了させ、問題があれば例外を送出させます。

``example/example-script`` には、より大規模なスクリプトの例があります。また、 ``plugins`` の下にはコマンドの定義例がいくつかあります。参考にしてみてください。


プロンプトモード
=======================================================

``mt-chamber.py`` を ``--prompt`` で実行すると、プロンプトモードとなります。プロンプトモードでは、バックグラウンドでスクリプトが実行しながら、動作状況んも確認やデバッグを行うことができます。

プロンプトモードでは、表示される ``>>> `` に続けてコマンドを入力します。
デフォルトで以下のコマンドを実行できます。

* ``watch``: スクリプトの ``Watch`` で指定された変数の値を表示します。
  ```
  watch [name...]
  ```
  |引数         |説明                                                                         |
  |:------------|:----------------------------------------------------------------------------|
  |``name...``  |表示するウォッチの名前。空の場合は全てのウォッチが表示されます。複数指定可。 |

* ``pause``: スクリプトを一時停止します。
  ```
  pause
  ```

* ``start``: 一時停止したスクリプトを再開します。
  ```
  start
  ```

* ``exit``: スクリプトが終了している場合は、プロンプトを閉じます。これは <kbd>CTRL</kbd>+<kbd>D</kbd> でも行えます。
  ```
  exit
  ```

* ``kill``: スクリプトの実行を中断します。
  ```
  kill
  ```


名前の由来
=======================================================

作者の出身は「楽器のまち（浜松市）」なので、音楽に由来する名前を考えました。
各コマンドを楽器に例えるならば、このプログラムは室内楽を奏でるための広間 (Chamber) です。