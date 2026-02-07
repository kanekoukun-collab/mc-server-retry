// サーバー状態を取得して表示
async function updateServerStatus() {
    try {
        const currentAddress = document.getElementById('server-address-btn').textContent;
        const response = await fetch(`/api/status?server=${encodeURIComponent(currentAddress)}`);
        const data = await response.json();

        // ローディングを非表示、コンテンツを表示
        document.getElementById('loading').style.display = 'none';
        document.getElementById('content').style.display = 'block';

        const statusBadge = document.getElementById('status-badge');
        const statusText = document.getElementById('status-text');
        const serverIcon = document.getElementById('server-icon');

        // エラーメッセージの確認
        if (data.error) {
            // ===== サーバーが見つからない =====
            statusBadge.textContent = '❌ 見つかりません';
            statusBadge.className = 'badge offline';
            statusText.textContent = data.error;

            serverIcon.style.display = 'none';

            document.getElementById('ping').textContent = 'N/A';
            document.getElementById('version').textContent = 'N/A';
            document.getElementById('players').textContent = '0 / 0';

            document.getElementById('players-container').style.display = 'none';
        } else if (data.online) {
            // ===== オンライン =====
            statusBadge.textContent = '🟢 Online';
            statusBadge.className = 'badge online';
            statusText.textContent = 'サーバーはオンラインです';

            // サーバーアイコン
            if (data.icon) {
                serverIcon.src = data.icon;
                serverIcon.style.display = 'block';
            } else {
                serverIcon.style.display = 'none';
            }

            // Ping
            document.getElementById('ping').textContent =
                data.ping !== undefined ? `${data.ping} ms` : 'N/A';

            // バージョン
            document.getElementById('version').textContent =
                data.version || 'N/A';

            // プレイヤー数
            if (data.players) {
                document.getElementById('players').textContent =
                    `${data.players.online} / ${data.players.max}`;

                if (data.players.online > 0 && data.players.list.length > 0) {
                    displayPlayers(data.players.list);
                } else {
                    document.getElementById('players-container').style.display = 'none';
                }
            }

        } else {
            // ===== オフライン =====
            statusBadge.textContent = '🔴 Offline';
            statusBadge.className = 'badge offline';
            statusText.textContent = 'サーバーはオフラインです';

            serverIcon.style.display = 'none';

            document.getElementById('ping').textContent = 'N/A';
            document.getElementById('version').textContent = 'N/A';
            document.getElementById('players').textContent = '0 / 0';

            document.getElementById('players-container').style.display = 'none';
        }

        // 最終更新時刻
        const updateTime = new Date(data.timestamp);
        document.getElementById('last-update').textContent =
            updateTime.toLocaleString('ja-JP');

    } catch (error) {
        console.error('Error fetching server status:', error);
        document.getElementById('status-text').textContent =
            '接続エラーが発生しました';
    }
}

// プレイヤーリストを表示
function displayPlayers(playersList) {
    const container = document.getElementById('players-container');
    const playersListElement = document.getElementById('players-list');

    playersListElement.innerHTML = '';

    playersList.forEach(player => {
        const playerCard = document.createElement('div');
        playerCard.className = 'player-card';

        const avatar = document.createElement('img');
        avatar.className = 'player-avatar';
        avatar.src = player.avatar || '/static/default-avatar.png';
        avatar.alt = player.name;

        const name = document.createElement('div');
        name.className = 'player-name';
        name.textContent = player.name;

        playerCard.appendChild(avatar);
        playerCard.appendChild(name);
        playersListElement.appendChild(playerCard);
    });

    container.style.display = 'block';
}

// 初回読み込み
updateServerStatus();

// 2秒ごとに常に更新
setInterval(updateServerStatus, 2000);

// ==================== 設定モーダル機能 ====================

// サーバーアドレスの取得・保存
const STORAGE_KEY = 'minecraft_server_address';

function loadServerAddress() {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved || 'gatisaba.xgames.jp'; // デフォルト値
}

function saveServerAddress(address) {
    localStorage.setItem(STORAGE_KEY, address);
}

// モーダルの要素を取得
const modal = document.getElementById('settings-modal');
const serverAddressBtn = document.getElementById('server-address-btn');
const closeBtn = document.getElementById('close-modal');
const cancelBtn = document.getElementById('cancel-btn');
const saveBtn = document.getElementById('save-btn');
const inputField = document.getElementById('server-address-input');

// モーダルを開く
serverAddressBtn.addEventListener('click', () => {
    inputField.value = serverAddressBtn.textContent;
    modal.classList.add('show');
    inputField.focus();
    inputField.select();
});

// モーダルを閉じる
function closeModal() {
    modal.classList.remove('show');
}

closeBtn.addEventListener('click', closeModal);
cancelBtn.addEventListener('click', closeModal);

// モーダルの外側をクリックして閉じる
modal.addEventListener('click', (e) => {
    if (e.target === modal) {
        closeModal();
    }
});

// 保存ボタン
saveBtn.addEventListener('click', async () => {
    const newAddress = inputField.value.trim();
    
    if (!newAddress) {
        alert('サーバーアドレスを入力してください');
        return;
    }
    
    // サーバーアドレスを更新
    saveServerAddress(newAddress);
    serverAddressBtn.textContent = newAddress;
    closeModal();
    
    console.log('✅ サーバーアドレスを更新:', newAddress);
    
    // 即座に新しいサーバーの情報を取得・表示
    await updateServerStatus();
});

// Enterキーで保存
inputField.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        saveBtn.click();
    }
});

// Escapeキーでモーダルを閉じる
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal.classList.contains('show')) {
        closeModal();
    }
});
