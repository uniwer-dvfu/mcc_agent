// Элементы страницы
const searchBtn = document.getElementById('searchBtn');
const resultContainer = document.getElementById('resultContainer');
const neuralContainer = document.getElementById('neuralContainer');
const orgNameInput = document.getElementById('orgName');
const addressInput = document.getElementById('address');

// Элементы для инструкции
const instructionModal = document.getElementById('instructionModal');
const openInstructionBtn = document.getElementById('openInstructionBtn');
const instructionClose = document.getElementById('instructionClose');

// Элементы для обратной связи
const feedbackModal = document.getElementById('feedbackModal');
const openFeedbackBtn = document.getElementById('openFeedbackBtn');
const feedbackClose = document.getElementById('feedbackClose');
const cancelFeedback = document.getElementById('cancelFeedback');
const submitFeedback = document.getElementById('submitFeedback');
const feedbackStatus = document.getElementById('feedbackStatus');
const fileInput = document.getElementById('attachments');
const fileList = document.getElementById('fileList');

let neurons = [];
let connections = [];
let neuralNetworkBuilt = false;
let currentMCCData = null;

// Отображение выбранных файлов
fileInput.addEventListener('change', function() {
    const files = Array.from(this.files);
    if (files.length > 0) {
        fileList.innerHTML = files.map(file =>
            `<div class="file-item">📎 ${file.name} (${(file.size / 1024).toFixed(1)} KB)</div>`
        ).join('');
    } else {
        fileList.innerHTML = '';
    }
});

// Функции для инструкции
function openInstructionModal() {
    instructionModal.classList.add('active');
}

function closeInstructionModal() {
    instructionModal.classList.remove('active');
}

openInstructionBtn.addEventListener('click', openInstructionModal);
instructionClose.addEventListener('click', closeInstructionModal);

instructionModal.addEventListener('click', (e) => {
    if (e.target === instructionModal) {
        closeInstructionModal();
    }
});

// Функции для обратной связи
function openFeedbackModal() {
    feedbackModal.classList.add('active');
    document.getElementById('feedbackName').value = '';
    document.getElementById('feedbackEmail').value = '';
    document.getElementById('feedbackMessage').value = '';
    fileInput.value = '';
    fileList.innerHTML = '';
    feedbackStatus.innerHTML = '';
}

function closeFeedbackModal() {
    feedbackModal.classList.remove('active');
}

openFeedbackBtn.addEventListener('click', openFeedbackModal);
feedbackClose.addEventListener('click', closeFeedbackModal);

feedbackModal.addEventListener('click', (e) => {
    if (e.target === feedbackModal) {
        closeFeedbackModal();
    }
});

submitFeedback.addEventListener('click', async () => {
    const name = document.getElementById('feedbackName').value.trim();
    const email = document.getElementById('feedbackEmail').value.trim();
    const message = document.getElementById('feedbackMessage').value.trim();
    const files = fileInput.files;

    if (!name) {
        feedbackStatus.innerHTML = '<div style="color: #ff6b6b;">❌ Укажите ваше имя</div>';
        return;
    }

    if (!email || !email.includes('@') || !email.includes('.')) {
        feedbackStatus.innerHTML = '<div style="color: #ff6b6b;">❌ Укажите корректный email</div>';
        return;
    }

    if (!message || message.length < 10) {
        feedbackStatus.innerHTML = '<div style="color: #ff6b6b;">❌ Сообщение должно содержать минимум 10 символов</div>';
        return;
    }

    submitFeedback.disabled = true;
    feedbackStatus.innerHTML = '<div style="color: #b0ffc0;">⏳ Отправка...</div>';

    const formData = new FormData();
    formData.append('name', name);
    formData.append('email', email);
    formData.append('message', message);

    for (let i = 0; i < files.length; i++) {
        formData.append('attachments', files[i]);
    }

    try {
        const response = await fetch('/send_feedback', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            feedbackStatus.innerHTML = `<div style="color: #70ff90;">✅ ${data.message}</div>`;
            setTimeout(() => {
                closeFeedbackModal();
            }, 3000);
        } else {
            feedbackStatus.innerHTML = `<div style="color: #ff6b6b;">❌ ${data.error}</div>`;
        }
    } catch (error) {
        feedbackStatus.innerHTML = '<div style="color: #ff6b6b;">❌ Ошибка при отправке</div>';
    } finally {
        submitFeedback.disabled = false;
    }
});

// Функция для создания нейронной сети
function buildNeuralNetwork() {
    neuralContainer.innerHTML = '';
    neurons = [];
    connections = [];

    const width = window.innerWidth;
    const height = window.innerHeight;
    const neuronCount = 35;

    for (let i = 0; i < neuronCount; i++) {
        const isLarge = Math.random() < 0.2;
        const neuron = document.createElement('div');
        neuron.className = `neuron ${isLarge ? 'neuron-large' : ''}`;

        const x = Math.random() * width;
        const y = Math.random() * height;

        neuron.style.left = x + 'px';
        neuron.style.top = y + 'px';
        neuron.dataset.x = x;
        neuron.dataset.y = y;

        neuralContainer.appendChild(neuron);
        neurons.push(neuron);

        setTimeout(() => {
            neuron.classList.add('visible');
        }, i * 30);
    }

    setTimeout(() => {
        for (let i = 0; i < neurons.length; i++) {
            for (let j = i + 1; j < neurons.length; j++) {
                const x1 = parseFloat(neurons[i].style.left);
                const y1 = parseFloat(neurons[i].style.top);
                const x2 = parseFloat(neurons[j].style.left);
                const y2 = parseFloat(neurons[j].style.top);

                const distance = Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));

                if (distance < 250 && Math.random() < 0.6) {
                    createConnection(neurons[i], neurons[j]);
                }
            }
        }
    }, 500);

    neuralContainer.classList.add('visible');
    neuralNetworkBuilt = true;
}

function createConnection(neuron1, neuron2) {
    const connection = document.createElement('div');
    connection.className = 'connection';

    const x1 = parseFloat(neuron1.style.left);
    const y1 = parseFloat(neuron1.style.top);
    const x2 = parseFloat(neuron2.style.left);
    const y2 = parseFloat(neuron2.style.top);

    const dx = x2 - x1;
    const dy = y2 - y1;
    const distance = Math.sqrt(dx * dx + dy * dy);
    const angle = Math.atan2(dy, dx) * 180 / Math.PI;

    connection.style.left = x1 + 'px';
    connection.style.top = y1 + 'px';
    connection.style.width = distance + 'px';
    connection.style.transform = `rotate(${angle}deg)`;

    neuralContainer.appendChild(connection);
    connections.push({ element: connection, neuron1, neuron2 });

    setTimeout(() => {
        connection.classList.add('visible');
    }, 100);
}

function activateNeuralNetwork() {
    if (!neuralNetworkBuilt) return;

    const activeCount = 5 + Math.floor(Math.random() * 5);

    for (let i = 0; i < activeCount; i++) {
        setTimeout(() => {
            const randomNeuron = neurons[Math.floor(Math.random() * neurons.length)];
            randomNeuron.classList.add('active-neuron');

            setTimeout(() => {
                randomNeuron.classList.remove('active-neuron');
            }, 300);
        }, i * 100);
    }

    setTimeout(() => {
        for (let i = 0; i < Math.min(8, connections.length); i++) {
            const randomConn = connections[Math.floor(Math.random() * connections.length)];
            randomConn.element.classList.add('active-connection');

            setTimeout(() => {
                randomConn.element.classList.remove('active-connection');
            }, 400);
        }
    }, 200);
}

function showLoader() {
    resultContainer.innerHTML = `
        <div class="loader">
            <div class="neural-spinner">
                <div class="neural-spinner-circle"></div>
                <div class="neural-spinner-circle"></div>
                <div class="neural-spinner-circle"></div>
            </div>
            <div style="color: white; font-size: 18px;">Поиск организации...</div>
            <div style="color: rgba(180,255,190,0.6); margin-top: 10px;">Этап 1: поиск здания</div>
        </div>
    `;

    for (let i = 0; i < 5; i++) {
        setTimeout(() => activateNeuralNetwork(), i * 200);
    }
}

function showToast(message, isError = false) {
    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.style.background = isError
        ? 'rgba(200, 60, 60, 0.95)'
        : 'rgba(30, 100, 50, 0.95)';
    toast.innerHTML = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}

async function reportWrongMCC() {
    if (!currentMCCData) {
        showToast('❌ Нет данных о текущем МСС-коде', true);
        return;
    }

    const reportData = {
        org_name: currentMCCData.org_name,
        address: currentMCCData.address,
        wrong_mcc: currentMCCData.mcc_code,
        wrong_mcc_name: currentMCCData.mcc_name,
        building_name: currentMCCData.building_name,
        building_address: currentMCCData.building_address,
        rubrics: currentMCCData.rubrics || [],
        services: currentMCCData.services || []
    };

    const btn = document.getElementById('reportWrongMccBtn');
    if (!btn) return;
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span>⏳</span> Отправка...';
    btn.disabled = true;

    try {
        const response = await fetch('/report_wrong_mcc', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(reportData)
        });

        const data = await response.json();

        if (data.success) {
            showToast('✅ Данная ошибка зафиксирована и отправлена! Благодарим за обратную связь');
        } else {
            showToast(`❌ Ошибка: ${data.error || 'Не удалось отправить'}`, true);
        }
    } catch (error) {
        showToast('❌ Ошибка при отправке. Попробуйте позже.', true);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

function showResult(data) {
    if (!data.success) {
        let errorHtml = `<div class="error-message">❌ ${data.error}</div>`;

        if (data.building) {
            errorHtml += `
                <div class="result-card">
                    <div class="building-info">
                        <div class="building-name">
                            <span>🏢</span> ${data.building.name || 'Здание'}
                        </div>
                        <div class="building-address">
                            <span>📍</span> ${data.building.address}
                        </div>
                        ${data.building.purpose ? `<div class="building-purpose">${data.building.purpose}</div>` : ''}
                    </div>
                    <div style="text-align: center; color: rgba(255,255,255,0.7); padding: 20px;">
                        Организация с таким названием не найдена в этом здании
                    </div>
                </div>
            `;
        }

        resultContainer.innerHTML = errorHtml;
        return;
    }

    const mcc = data.mcc;
    const org = data.organization;
    const building = data.building;

    // Сохраняем данные для кнопки "Неверный МСС"
    currentMCCData = {
        org_name: org.name,
        address: building.address,
        mcc_code: mcc.code,
        mcc_name: mcc.name,
        building_name: building.name,
        building_address: building.address,
        rubrics: org.rubrics || [],
        services: org.services || []
    };

    let rubricsHtml = '';
    if (org.rubrics && org.rubrics.length > 0) {
        rubricsHtml = org.rubrics.map(r => `<span class="rubric-tag">${r}</span>`).join('');
    }

    let servicesHtml = '';
    if (org.services && org.services.length > 0) {
        servicesHtml = `
            <div class="services-section">
                <div class="services-title">Услуги</div>
                <div class="services-tags">
                    ${org.services.map(s => `<span class="service-tag">${s}</span>`).join('')}
                </div>
            </div>
        `;
    }

    let matchesHtml = '';
    if (mcc.matches && mcc.matches.length > 0) {
        matchesHtml = `
            <div class="matches-badge">
                ${mcc.matches.map(m => `<span class="match-tag">${m}</span>`).join('')}
            </div>
        `;
    }

    let mccDescription = mcc.description ? `<div class="mcc-description">📋 ${mcc.description}</div>` : '';

    resultContainer.innerHTML = `
        <div class="result-card">
            <div class="result-header">
                <div class="result-icon">🎯</div>
                <h3>Результат поиска</h3>
            </div>

            <div class="building-info">
                <div class="building-name">
                    <span>🏢</span> ${building.name || 'Здание'}
                </div>
                <div class="building-address">
                    <span>📍</span> ${building.address}
                </div>
                ${building.purpose ? `<div class="building-purpose">${building.purpose}</div>` : ''}
            </div>

            <div class="org-info">
                <div class="org-name">${org.name}</div>
                <div class="rubrics">${rubricsHtml}</div>
                ${servicesHtml}
            </div>

            <div class="mcc-result">
                <div class="mcc-code">${mcc.code}</div>
                <div class="mcc-name">${mcc.name}</div>
                ${mccDescription}
                ${matchesHtml}
                <div class="confidence-meter">
                    <div class="confidence-label">
                        <span>Уверенность</span>
                        <span>${mcc.confidence}%</span>
                    </div>
                    <div class="confidence-bar">
                        <div class="confidence-fill" style="width: ${mcc.confidence}%"></div>
                    </div>
                </div>

                <div style="display: flex; gap: 15px; justify-content: center; margin-top: 20px;">
                    <button class="wrong-mcc-button" id="reportWrongMccBtn" onclick="reportWrongMCC()">
                        <span>🚫</span> Неверный МСС
                    </button>
                    <button class="recommendations-button" id="recommendationsBtn" onclick="showRecommendations()">
                        <span>📊</span> Рекомендации по продажам
                    </button>
                </div>
            </div>
        </div>
    `;

    for (let i = 0; i < 8; i++) {
        setTimeout(() => activateNeuralNetwork(), i * 150);
    }
}

searchBtn.addEventListener('click', async () => {
    const orgName = orgNameInput.value.trim();
    const address = addressInput.value.trim();

    if (!orgName || !address) {
        alert('Пожалуйста, заполните оба поля');
        return;
    }

    searchBtn.disabled = true;
    showLoader();

    try {
        const response = await fetch('/search_organization', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                org_name: orgName,
                address: address
            })
        });

        const data = await response.json();
        showResult(data);

    } catch (error) {
        resultContainer.innerHTML = `
            <div class="error-message">❌ Ошибка при поиске: ${error.message}</div>
        `;
    } finally {
        searchBtn.disabled = false;
    }
});

addressInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        searchBtn.click();
    }
});

// Закрытие модальных окон по Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        if (instructionModal.classList.contains('active')) {
            closeInstructionModal();
        }
        if (feedbackModal.classList.contains('active')) {
            closeFeedbackModal();
        }
    }
});

// Строим нейросеть при загрузке
setTimeout(() => {
    buildNeuralNetwork();
}, 500);

// ========== ФУНКЦИЯ РЕКОМЕНДАЦИЙ ПО ПРОДАЖАМ ==========

// Списки MCC-кодов
const POS_CREDIT_ALLOWED = new Set([
    '5977', '5193', '7538', '7535', '5013', '5532', '5533', '5551', '5571',
    '8021', '8043', '7298', '5137', '5611', '5621', '5661', '5641', '5651',
    '5655', '5948', '5691', '5699', '5944', '7997', '5941', '5733', '5940',
    '5996', '5598', '5947', '5999', '5021', '5074', '5231', '5251', '5200',
    '5261', '5712', '5713', '5714', '5719', '5211', '5047', '4812', '5045',
    '5072', '5734', '5817', '5722', '5732', '5946', '5945', '4112', '4722',
    '1740', '1771', '5065', '5198', '5718', '5975', '5997', '7032', '7531',
    '1520', '5521', '8099', '5995', '5541', '7011', '5511', '5976', '5631',
    '8042', '5139', '5681', '5131', '5094', '7922', '7991', '5735', '7994',
    '5949', '5192', '5942', '5331', '5310', '5399', '5311', '5039', '5531',
    '5950', '0780', '7998', '1711', '1731', '1750', '1761', '1799', '5422',
    '5816', '5818', '7622', '7629', '5044', '5697', '7221', '7379', '7623',
    '7631', '7641', '7699', '6300', '8999', '7999', '8299', '7299', '3011',
    '4011', '4789', '4468', '5815', '5978', '7692', '5051', '4411', '8244',
    '8249', '7333', '7395', '8241', '8911', '8675', '7523', '7542', '7534',
    '3692', '5599', '5698', '7230', '7297', '8011', '8050', '8062', '8071',
    '5931', '7911', '7941', '7996', '5971', '5943', '5111', '5992', '0742',
    '7210', '7216', '7217', '7311', '7349', '7394', '6513', '6211', '7512',
    '4111', '4511', '4582', '7033', '8211', '8220', '3089', '3778', '3779',
    '4457', '5300', '5937', '5970', '5998', '7251', '7296', '7519', '8049',
    '5592', '7513', '4214', '4225', '5561', '7992', '7211', '7278', '7342'
]);

const POS_CREDIT_FORBIDDEN = new Set([
    '5983', '4784', '9222', '9311', '9399', '5811', '5812', '5814', '5813',
    '5122', '5912', '7832', '7841', '7932', '7933', '7995', '5932', '5973',
    '5309', '4816', '4121', '4215', '4899', '4900', '7392', '7261', '8111',
    '8931', '5933', '4131', '6051', '8398', '8661', '8699', '5411', '5441',
    '5451', '5462', '5499', '5921', '5993', '763', '4119', '4814', '4829',
    '5046', '5542', '5552', '5972', '6010', '6011', '6540', '7273', '7393',
    '7549', '8031', '8041', '9406', '5994', '7338', '7361', '7375', '2741',
    '7993', '8351', '6012', '7276', '7277', '7339', '7399', '9402', '8641', '8651'
]);

// Списки для СберЧаевых
const SBERTIPS_ALLOWED = new Set([
    '5812', '5814', '5813', '7011', '3501', '3504', '3509', '3604', '4215', '5300', '7230', '7298'
]);

const SBERTIPS_FORBIDDEN = new Set([
    '9311', '7261', '9399', '8211', '8661', '8062', '7995', '6513', '5122', '5921', '5993', '6211', '6051', '6050', '7012'
]);

// Функция для получения рекомендаций по продажам
function getSalesRecommendations(mccCode, mccName, businessName) {
    const recommendations = {
        hasPosCredit: false,
        posCreditMessage: '',
        hasSberTips: false,
        sberTipsMessage: '',
        generalMessage: '',
        showButton: true
    };

    // 1. Проверка POS-кредитования
    if (POS_CREDIT_ALLOWED.has(mccCode)) {
        recommendations.hasPosCredit = true;
        recommendations.posCreditMessage = `✅ POS-кредитование доступно для МСС-кода ${mccCode} (${mccName}).
        \nРекомендуем предложить клиенту оформление покупки в рассрочку или кредит прямо на месте.
        \n🎯 Выгода: повышение среднего чека до 40%, увеличение конверсии в продажу.`;
    } else if (POS_CREDIT_FORBIDDEN.has(mccCode)) {
        recommendations.hasPosCredit = false;
        recommendations.posCreditMessage = `❌ POS-кредитование НЕ доступно для МСС-кода ${mccCode} (${mccName}).
        \nДанный вид деятельности не подходит для рассрочки/кредита на месте.`;
    } else {
        recommendations.hasPosCredit = false;
        recommendations.posCreditMessage = `⚠️ POS-кредитование для МСС-кода ${mccCode} (${mccName}) требует дополнительной проверки.
        \nОбратитесь в отдел риск-менеджмента для уточнения возможности подключения.`;
    }

    // 2. Проверка СберЧаевых
    if (SBERTIPS_ALLOWED.has(mccCode)) {
        recommendations.hasSberTips = true;
        recommendations.sberTipsMessage = `💬 СберЧаевые рекомендуются для МСС-кода ${mccCode} (${mccName})!
        \nПредложите клиенту подключение сервиса для приёма чаевых через СБП.
        \n🎯 Преимущества: безналичные чаевые, лёгкое подключение, прозрачная отчётность.`;
    } else if (SBERTIPS_FORBIDDEN.has(mccCode)) {
        recommendations.hasSberTips = false;
        recommendations.sberTipsMessage = `❌ СберЧаевые НЕ рекомендуются для МСС-кода ${mccCode} (${mccName}).`;
    } else {
        recommendations.hasSberTips = false;
        recommendations.sberTipsMessage = `🤔 Для МСС-кода ${mccCode} (${mccName}) возможность подключения СберЧаевых требует уточнения.`;
    }

    // 3. Общая рекомендация на основе типа бизнеса
    if (POS_CREDIT_ALLOWED.has(mccCode) && SBERTIPS_ALLOWED.has(mccCode)) {
        recommendations.generalMessage = `🏆 Универсальное предложение: клиенту подходят оба продукта!
        \n1️⃣ POS-кредитование — для увеличения среднего чека
        \n2️⃣ СберЧаевые — для дополнительного дохода от клиентов

        \n📞 Рекомендуем провести встречу и презентовать оба решения.`;
    } else if (POS_CREDIT_ALLOWED.has(mccCode)) {
        recommendations.generalMessage = `📈 Ключевая рекомендация: предложите клиенту POS-кредитование.
        \nЭто идеальный продукт для бизнеса с МСС-кодом ${mccCode}.
        \n🎯 Продающий скрипт: «Увеличьте свои продажи — предложите клиентам рассрочку прямо на кассе».`;
    } else if (SBERTIPS_ALLOWED.has(mccCode)) {
        recommendations.generalMessage = `💡 Ключевая рекомендация: предложите клиенту СберЧаевые.
        \nЭтот продукт идеально подходит для вашего типа бизнеса.
        \n🎯 Продающий скрипт: «Позвольте клиентам благодарить вас рублём — подключите безналичные чаевые».`;
    } else {
        recommendations.generalMessage = `🤝 Рекомендуем провести дополнительный анализ потребностей клиента.
        \nМСС-код ${mccCode} (${mccName}) не входит в стандартные продуктовые матрицы.
        \n🎯 Предложите базовый эквайринг и дополнительные сервисы от Сбера.`;
    }

    return recommendations;
}

// Функция для отображения рекомендаций в модальном окне
function showRecommendationsModal(recommendations, businessName, mccCode, mccName) {
    // Удаляем старое модальное окно, если есть
    const existingModal = document.getElementById('recommendationsModal');
    if (existingModal) existingModal.remove();

    // Создаём модальное окно
    const modal = document.createElement('div');
    modal.id = 'recommendationsModal';
    modal.className = 'modal-overlay';
    modal.style.display = 'flex';
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 550px;">
            <div class="modal-header">
                <h2>
                    <span>📊</span> Рекомендации по продажам
                </h2>
                <div class="modal-close" onclick="document.getElementById('recommendationsModal').remove()">✕</div>
            </div>

            <div style="margin-bottom: 10px; padding: 12px; background: rgba(60,200,100,0.15); border-radius: 16px;">
                <div style="font-size: 14px; color: rgba(255,255,255,0.7);">Торговая точка:</div>
                <div style="font-size: 18px; font-weight: 600; color: #b0ffc0;">${escapeHtml(businessName)}</div>
                <div style="font-size: 13px; color: rgba(255,255,255,0.6); margin-top: 5px;">MCC: ${mccCode} — ${escapeHtml(mccName)}</div>
            </div>

            <div style="margin-bottom: 20px;">
                <div style="background: rgba(60,200,100,0.1); border-radius: 16px; padding: 15px; margin-bottom: 12px;">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                        <span style="font-size: 24px;">💰</span>
                        <span style="font-weight: 700; color: #b0ffc0;">POS-кредитование</span>
                    </div>
                    <p style="color: rgba(255,255,255,0.85); font-size: 14px; line-height: 1.5; white-space: pre-line;">${recommendations.posCreditMessage}</p>
                </div>

                <div style="background: rgba(60,200,100,0.1); border-radius: 16px; padding: 15px; margin-bottom: 12px;">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                        <span style="font-size: 24px;">💬</span>
                        <span style="font-weight: 700; color: #b0ffc0;">СберЧаевые</span>
                    </div>
                    <p style="color: rgba(255,255,255,0.85); font-size: 14px; line-height: 1.5; white-space: pre-line;">${recommendations.sberTipsMessage}</p>
                </div>

                <div style="background: linear-gradient(135deg, rgba(30,100,50,0.3), rgba(20,60,40,0.3)); border-radius: 16px; padding: 15px; border-left: 4px solid #4CAF50;">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                        <span style="font-size: 24px;">🎯</span>
                        <span style="font-weight: 700; color: #b0ffc0;">Продажная рекомендация</span>
                    </div>
                    <p style="color: rgba(255,255,255,0.9); font-size: 14px; line-height: 1.5; white-space: pre-line;">${recommendations.generalMessage}</p>
                </div>
            </div>

            <!-- Убрана кнопка "Закрыть", осталась только "Запросить подключение" -->
            <button class="ios-button" onclick="window.open('https://www.sberbank.ru/ru/small_business/acquiring', '_blank')" style="width: 100%; background: rgba(30,100,50,0.8);">
                📞 Запросить подключение
            </button>
        </div>
    `;

    document.body.appendChild(modal);

    // Закрытие по клику на фон
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
}


// Функция для обработки нажатия на кнопку рекомендаций
async function showRecommendations() {
    if (!currentMCCData) {
        showToast('❌ Нет данных о текущем МСС-коде', true);
        return;
    }

    const { mcc_code, mcc_name, org_name } = currentMCCData;

    showToast('📊 Загружаем рекомендации...');

    setTimeout(() => {
        const recommendations = getSalesRecommendations(mcc_code, mcc_name, org_name);
        showRecommendationsModal(recommendations, org_name, mcc_code, mcc_name);
    }, 300);
}

// Функция для экранирования HTML
function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}