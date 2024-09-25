import streamlit as st
import mysql.connector
import time
import random

# ページコンフィグ
st.set_page_config(
    initial_sidebar_state="collapsed"
)

# タイトル
st.title('🎒Streamlit Forumへようこそ🎒')

# Connect to TiDB
@st.cache_resource(ttl=600)
def connect_to_tidb(autocommit=True):
    connection = mysql.connector.connect(
        host = st.secrets.tidb.host,
        port = st.secrets.tidb.port,
        user = st.secrets.tidb.user,
        password = st.secrets.tidb.password,
        database = st.secrets.tidb.database,
        autocommit = autocommit,
        use_pure = True
    )
    return connection

# 映像リソースを取得
@st.cache_data
def get_video_resource():
    with open("resources/lot.mp4", 'rb') as f:
        return f.read()

# 画像リソースを取得
@st.cache_data
def get_image_resource(item):
    if item == "socks":
        with open("resources/result_socks.png", 'rb') as f:
            return f.read()
    elif item == "backpack":
        with open("resources/result_backpack.png", 'rb') as f:
            return f.read()

# 抽選処理
def lottery():
    # 抽選の流れ
    # 1. トランザクション開始
    # 2. itemsテーブルから各アイテムのitem_stockを取得
    # 3. 取得したitem_stockから抽選テーブルを作成
    # 4. randomで抽選
    # 5. 抽選結果をitemsテーブルに反映
    # 6. トランザクションコミット
    # 7. 抽選結果をセット

    # TiDBに接続
    connection = connect_to_tidb()
    cursor = connection.cursor()

    # 所要時間を計測開始
    start_time = time.time()

    # トランザクション開始
    cursor.execute("START TRANSACTION;")

    # itemsテーブルから各アイテムのitem_stockを取得
    cursor.execute("SELECT * FROM items FOR UPDATE;")
    items = cursor.fetchall()

    # 取得したitem_stockから抽選テーブルを作成
    lot_buffer = dict()
    start_value = 0
    end_value = 0
    for item in items:
        if item[2] <= 0:
            continue
        end_value = start_value + item[2]
        lot_buffer[item[1]] = [start_value, end_value, item[0], item[2]]
        start_value = end_value
    # デバッグ表示
    st.write(lot_buffer)

    # randomで抽選
    if end_value > 0:
        random_value = random.randrange(0, end_value)
    else:
        # item_stockが0以下の場合は抽選しない
        random_value = 0
    result_item = "socks"
    for key, value in lot_buffer.items():
        if value[0] <= random_value < value[1]:
            result_item = key
            break
    # デバッグ表示
    st.write(f"抽選結果: {result_item} ({random_value})")

    # 抽選結果をitemsテーブルに反映
    cursor.execute(f"UPDATE items SET item_stock = item_stock - 1 WHERE item_name = \"{result_item}\";")

    # トランザクションコミット
    cursor.execute("COMMIT;")

    # 抽選結果をセット
    set_lottery_result(result_item)

    # ログを出力
    if result_item in lot_buffer:
        item_key = lot_buffer[result_item][2]
        item_stock_before = lot_buffer[result_item][3]
        item_stock_after = item_stock_before - 1
    else:
        # item_stockが0以下で抽選しなかった場合のログ
        item_key = -1
        item_stock_before = 0
        item_stock_after = -1
    cursor.execute(f"INSERT INTO lot_logs (lot_time, item_key, item_stock_before, item_stock_after) VALUES (NOW(), {item_key}, {item_stock_before}, {item_stock_after});")

    # 所要時間を計測終了
    end_time = time.time()
    time_diff = end_time - start_time
    if time_diff < 5:
        # 5秒未満の場合は差の分だけ待つ
        time.sleep(5 - time_diff)

# セッションステート取得用ラッパー：画面を取得
def get_current_scene():
    if "scene" not in st.session_state:
        st.session_state.scene = "waiting"
    return st.session_state.scene

# セッションステート更新用ラッパー：画面を変更
def set_current_scene(scene):
    st.session_state.scene = scene

# セッションステート取得用ラッパー：抽選結果を取得
def get_lottery_result():
    if "lottery_result" not in st.session_state:
        st.session_state.lottery_result = "socks"
    return st.session_state.lottery_result

# セッションステート更新用ラッパー：抽選結果を設定
def set_lottery_result(lottery_result):
    st.session_state.lottery_result = lottery_result

# セッションステートの取得
scene = get_current_scene()

# 抽選待ち画面
if scene == "waiting":
    # 抽選ボタン
    if st.button('抽選する'):
        set_current_scene("lottery")
        st.rerun()

# 抽選中画面
elif scene == "lottery":
    # 抽選中のビデオを表示する
    st.video(get_video_resource(), start_time=0, loop=False, autoplay=True)

    # 抽選したら次の画面に遷移
    lottery()
    set_current_scene("result")
    st.rerun()

# 抽選結果画面
elif scene == "result":
    # 抽選結果を取得
    result = get_lottery_result()

    # 抽選結果画面
    if result == "socks":
        st.image(get_image_resource("socks"), use_column_width=True)
        st.balloons()
    elif result == "backpack":
        st.image(get_image_resource("backpack"), use_column_width=True)
        st.snow()
    st.write('🎉おめでとうございます🎉')

    # 初期化ボタン
    if st.button('最初の画面に戻る'):
        set_current_scene("waiting")
        st.rerun()
