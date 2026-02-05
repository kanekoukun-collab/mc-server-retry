// サーバー状態を取得して表示
async function updateServerStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        // ローディングを非表示、コンテンツを表示
        document.getElementById('loading').style.display = 'none';
        document.getElementById('content').style.display = 'block';

        const statusBadge = document.getElementById('status-badge');
        const statusText = document.getElementById('status-text');
        const serverIcon = document.getElementById('server-icon');

        if (data.online) {
            // ===== オンライン =====
            statusBadge.textContent = '🟢 Online';
            statusBadge.className = 'badge online';

            // テキストを一度リセット（imgを残すため）
            statusText.childNodes[0].textContent = 'サーバーはオンラインです';

            // サーバーアイコン（右側）
            if (data.icon) {
                serverIcon.src = data.icon;
                serverIcon.style.display = 'inline-block';
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
            statusText.childNodes[0].textContent = 'サーバーはオフラインです';

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

// 5秒ごとに更新
setInterval(updateServerStatus, 5000);
