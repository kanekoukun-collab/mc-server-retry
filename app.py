from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import requests
import json
from datetime import datetime
import os
import base64
import uuid
import logging
import sys
from mcstatus import JavaServer
from functools import wraps

app = Flask(__name__)

# シークレットキー設定
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# セッション設定
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'  # 本番環境ではTrue
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1時間

# 管理者パスワード
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# ログ設定（Render対応）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)
logger.info("=== Minecraft Server Monitor 起動 ===")

# サーバー設定
SERVER_ADDRESS = "gatisaba.xgames.jp"
SERVER_PORT = 25565
API_URL = f"https://api.mcsrvstat.us/3/{SERVER_ADDRESS}"

def get_minecraft_ping(server_address=SERVER_ADDRESS):
    """Minecraftサーバーに直接接続してping値を取得"""
    try:
        logger.info(f"📡 Minecraftサーバーのping値を計測中: {server_address}:{SERVER_PORT}")
        
        # JavaServerに直接接続
        server = JavaServer.lookup(f"{server_address}:{SERVER_PORT}")
        status = server.status()
        
        # ピング値をミリ秒の整数に丸める
        raw_ping = int(round(status.latency))
        
        # mcstatusが返す値はハンドシェイク時間なので、実際のpingに変換
        # 調整値: 63 ms (実験値)
        actual_ping = max(0, raw_ping - 63)
        
        logger.info(f"✅ Ping値を取得: {actual_ping} ms (raw: {raw_ping} ms)")
        return actual_ping
    except Exception as e:
        logger.error(f"❌ Minecraftサーバーのping計測エラー: {str(e)}")
        return None

def get_minecraft_ping_for_server(server_address):
    """動的サーバーアドレス対応のping計測"""
    return get_minecraft_ping(server_address)

def download_image(url):
    """画像をダウンロードしてBase64に変換"""
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return base64.b64encode(response.content).decode('utf-8')
    except Exception as e:
        logger.warning(f"画像ダウンロードエラー {url}: {e}")
        return None

def get_player_avatar(player_uuid):
    """UUIDからプレイヤーの頭画像を取得"""
    if not player_uuid:
        return get_default_avatar()
    
    # Crafatarからアバターを取得
    avatar_url = f"https://crafatar.com/avatars/{player_uuid}?size=64&overlay=true"
    
    # 代替URL（Crafatarが失敗した場合）
    fallback_urls = [
        f"https://mc-heads.net/avatar/{player_uuid}/64",
        f"https://minotar.net/avatar/{player_uuid}/64.png",
        f"https://visage.surgeplay.com/face/64/{player_uuid}"
    ]
    
    # Crafatarを試す
    avatar_data = download_image(avatar_url)
    if avatar_data:
        return f"data:image/png;base64,{avatar_data}"
    
    # Crafatarが失敗したら代替サービスを試す
    for fallback_url in fallback_urls:
        avatar_data = download_image(fallback_url)
        if avatar_data:
            return f"data:image/png;base64,{avatar_data}"
    
    # すべて失敗したらデフォルト
    return get_default_avatar()

def get_default_avatar():
    """デフォルトのSteveの頭を返す"""
    steve_uuid = "8667ba71-b85a-4004-af54-457a9734eed7"
    avatar_url = f"https://crafatar.com/avatars/{steve_uuid}?size=64"
    avatar_data = download_image(avatar_url)
    if avatar_data:
        return f"data:image/png;base64,{avatar_data}"
    return None

@app.route('/')
def index():
    """メインページ"""
    return render_template('index.html', 
                         server_address=SERVER_ADDRESS,
                         server_port=SERVER_PORT)

@app.route('/api/status')
def api_status():
    """サーバー状態API"""
    # クエリパラメータからサーバーアドレスを取得（デフォルト: gatisaba.xgames.jp）
    server_addr = request.args.get('server', SERVER_ADDRESS)
    api_url = f"https://api.mcsrvstat.us/3/{server_addr}"
    
    logger.info(f"📡 APIリクエスト: {api_url}")
    
    response_data = {
        'online': False,
        'server': server_addr,
        'port': SERVER_PORT,
        'timestamp': datetime.utcnow().isoformat(),
        'players': {
            'online': 0,
            'max': 0,
            'list': []
        },
        'error': None  # エラーメッセージ
    }
    
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        logger.info(f"✓ APIレスポンス成功 | online={data.get('online')}")
    except requests.exceptions.Timeout:
        logger.error(f"❌ APIタイムアウト: {server_addr}")
        response_data['error'] = f"サーバーが見つかりませんでした ({server_addr})"
        return jsonify(response_data)
    except requests.exceptions.ConnectionError:
        logger.error(f"❌ 接続エラー: {server_addr}")
        response_data['error'] = f"サーバーが見つかりませんでした ({server_addr})"
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"❌ APIエラー: {str(e)}")
        response_data['error'] = f"サーバーが見つかりませんでした ({server_addr})"
        return jsonify(response_data)
    
    # サーバー情報が取得できたかチェック
    if data and 'online' in data:
        # サーバーは存在する
        if data.get('online'):
            # オンライン
            response_data['online'] = True
            
            # 基本情報をコピー
            for key in ['version', 'protocol', 'hostname', 'software', 'motd']:
                if key in data:
                    response_data[key] = data[key]
            
            # ★ Ping値を直接計測
            ping_value = get_minecraft_ping_for_server(server_addr)
            if ping_value is not None:
                response_data['ping'] = ping_value
                logger.info(f"✅ Ping値をレスポンスに追加: {ping_value} ms")
            else:
                logger.warning(f"⚠️ Ping値の取得に失敗しました")
            
            # プレイヤー情報
            players = data.get('players', {})
            response_data['players']['online'] = players.get('online', 0)
            response_data['players']['max'] = players.get('max', 0)
            
            # プレイヤーリスト処理
            player_list = []
            if players.get('online', 0) > 0 and 'list' in players:
                for player_item in players['list']:
                    if isinstance(player_item, dict):
                        # オブジェクト形式: {"name": "...", "uuid": "..."}
                        player_name = player_item.get('name', '')
                        player_uuid = player_item.get('uuid', '')
                    else:
                        # 文字列形式（古いAPI）
                        player_name = str(player_item)
                        player_uuid = None
                    
                    if player_name:
                        player_info = {
                            'name': player_name,
                            'uuid': player_uuid,
                            'avatar': get_player_avatar(player_uuid)
                        }
                        player_list.append(player_info)
                        logger.info(f"プレイヤー処理: {player_name}, UUID: {player_uuid}")
            
            response_data['players']['list'] = player_list
            
            # アイコン
            if 'icon' in data:
                response_data['icon'] = data['icon']
        else:
            # オフライン（サーバーは存在するがオフライン状態）
            response_data['online'] = False
            response_data['error'] = None  # エラーではない
            
            # アイコン
            if 'icon' in data:
                response_data['icon'] = data['icon']
            
            logger.info(f"⚠️ サーバーはオフライン: {server_addr}")
    else:
        # サーバーが見つからない
        response_data['error'] = f"サーバーが見つかりませんでした ({server_addr})"
        logger.error(f"❌ サーバーが見つかりません: {server_addr}")
    
    logger.info(f"📤 APIステータスレスポンス: {response_data}")
    return jsonify(response_data)

@app.route('/api/debug')
def debug_api():
    """デバッグエンドポイント - APIレスポンスを確認"""
    data = get_server_status()
    ping_value = get_minecraft_ping()
    
    if data:
        return jsonify({
            'status': 'success',
            'raw_api_response': data,
            'ping_info': {
                'minecraft_ping': ping_value,
                'ping_type': str(type(ping_value).__name__) if ping_value else 'None',
            },
            'online': data.get('online'),
            'available_keys': sorted(list(data.keys()))
        })
    else:
        return jsonify({'status': 'error', 'message': 'API接続失敗'}), 500

@app.route('/api/test/avatar/<uuid>')
def test_avatar(uuid):
    """アバター取得テスト用エンドポイント"""
    avatar_data = get_player_avatar(uuid)
    
    result = {
        'uuid': uuid,
        'has_avatar': avatar_data is not None
    }
    
    if avatar_data:
        # プレビュー用に短縮
        result['avatar_preview'] = avatar_data[:100] + "..." if len(avatar_data) > 100 else avatar_data
    
    return jsonify(result)

@app.route('/api/test/player/<username>')
def test_player(username):
    """プレイヤー情報取得テスト"""
    try:
        # Mojang APIからUUID取得
        uuid_url = f"https://api.mojang.com/users/profiles/minecraft/{username}"
        response = requests.get(uuid_url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            uuid_short = data.get('id', '')
            
            # ハイフンありの形式に変換
            if uuid_short and len(uuid_short) == 32:
                uuid_full = str(uuid.UUID(uuid_short))
            else:
                uuid_full = uuid_short
            
            # アバター取得
            avatar_data = get_player_avatar(uuid_full)
            
            return jsonify({
                'username': username,
                'uuid_short': uuid_short,
                'uuid_full': uuid_full,
                'has_avatar': avatar_data is not None
            })
        else:
            return jsonify({
                'username': username,
                'error': f'APIエラー: {response.status_code}'
            }), 404
    except Exception as e:
        return jsonify({
            'username': username,
            'error': str(e)
        }), 500

# ==================== 管理者ページ ====================

def admin_required(f):
    """管理者認証チェックデコレーター"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('admin_authenticated'):
            return f(*args, **kwargs)
        return redirect(url_for('admin_login'))
    return decorated_function

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """管理者ログイン"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == ADMIN_PASSWORD:
            session['admin_authenticated'] = True
            logger.info("✅ 管理者がログインしました")
            return redirect(url_for('admin_panel'))
        else:
            logger.warning("❌ 管理者ログイン失敗: パスワード不一致")
            return render_template('admin_login.html', error='パスワードが違います')
    return render_template('admin_login.html')

@app.route('/admin', methods=['GET', 'POST'])
@admin_required
def admin_panel():
    """管理者パネル"""
    message = ''
    if request.method == 'POST':
        message = request.form.get('message', '')
        logger.info(f"📝 管理者がメッセージを送信: {len(message)} 文字")
    
    return render_template('admin_panel.html', message=message)

@app.route('/admin/logout')
def admin_logout():
    """ログアウト"""
    session.clear()
    logger.info("👋 管理者がログアウトしました")
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"🚀 サーバー起動: ポート {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
