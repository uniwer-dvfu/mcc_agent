// Элементы страницы
const searchBtn = document.getElementById('searchBtn');
const resultContainer = document.getElementById('resultContainer');
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
const submitFeedback = document.getElementById('submitFeedback');
const feedbackStatus = document.getElementById('feedbackStatus');
const fileInput = document.getElementById('attachments');
const fileList = document.getElementById('fileList');

let currentMCCData = null;
let currentCompany = { state: 'disabled', info: null };
let currentGeo = null;

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
    document.getElementById('feedbackBadgeNumber').value = '';
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
    const badgeNumber = document.getElementById('feedbackBadgeNumber').value.trim();
    const message = document.getElementById('feedbackMessage').value.trim();
    const files = fileInput.files;

    if (!name) {
        feedbackStatus.innerHTML = '<div style="color:var(--danger-text);">❌ Укажите ваше имя</div>';
        return;
    }

    if (!email || !email.includes('@') || !email.includes('.')) {
        feedbackStatus.innerHTML = '<div style="color:var(--danger-text);">❌ Укажите корректный email</div>';
        return;
    }

    // Валидация табельного номера (7 цифр)
    if (!badgeNumber) {
        feedbackStatus.innerHTML = '<div style="color:var(--danger-text);">❌ Укажите табельный номер (7 цифр)</div>';
        return;
    }

    if (!/^\d{7}$/.test(badgeNumber)) {
        feedbackStatus.innerHTML = '<div style="color:var(--danger-text);">❌ Табельный номер должен состоять из 7 цифр</div>';
        return;
    }

    if (!message || message.length < 10) {
        feedbackStatus.innerHTML = '<div style="color:var(--danger-text);">❌ Сообщение должно содержать минимум 10 символов</div>';
        return;
    }

    // Проверка на наличие прикреплённых файлов
    if (files.length === 0) {
        feedbackStatus.innerHTML = '<div style="color:var(--danger-text);">❌ Прикрепите файлы (терминальный чек, фото вывески и т.д.)</div>';
        return;
    }

    submitFeedback.disabled = true;
    feedbackStatus.innerHTML = '<div style="color:var(--accent-text);">⏳ Отправка...</div>';

    const formData = new FormData();
    formData.append('name', name);
    formData.append('email', email);
    formData.append('badge_number', badgeNumber);
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
            feedbackStatus.innerHTML = `<div style="color:var(--accent-text);">✅ ${data.message}</div>`;
            setTimeout(() => {
                closeFeedbackModal();
            }, 3000);
        } else {
            feedbackStatus.innerHTML = `<div style="color:var(--danger-text);">❌ ${data.error}</div>`;
        }
    } catch (error) {
        feedbackStatus.innerHTML = '<div style="color:var(--danger-text);">❌ Ошибка при отправке</div>';
    } finally {
        submitFeedback.disabled = false;
    }
});

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
                    <div style="text-align: center; color:var(--fg-medium); padding: 20px;">
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

    currentGeo = {
        lat: data.extra ? data.extra.lat : null,
        lon: data.extra ? data.extra.lon : null,
        org_id: data.extra ? data.extra.org_id : '',
        address: data.extra ? data.extra.query_address : ''
    };
    currentCompany = {
        state: (data.extra && data.extra.company_state) || 'disabled',
        info: (data.extra && data.extra.company) || null
    };

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

    // Блоки GigaChat (вынесены в отдельную переменную)
    // Справочная информация: бренд, график, ближайшие объекты
    let extraHtml = '';
    const extra = data.extra || {};
    const extraRows = [];
    if (extra.brand) extraRows.push(`<div>🏷️ <b>Бренд / сеть:</b> ${escapeHtml(extra.brand)}</div>`);
    if (extra.schedule) extraRows.push(`<div>🕒 <b>График:</b> ${escapeHtml(extra.schedule)}</div>`);
    if (extra.nearby && extra.nearby.length > 0) {
        const items = extra.nearby.map(n =>
            `<li>${escapeHtml(n.name)}${n.category ? ' — ' + escapeHtml(n.category) : ''}, ${n.distance_m} м</li>`
        ).join('');
        extraRows.push(`<div style="margin-top:6px;">📍 <b>Рядом (OpenStreetMap):</b><ul style="margin:4px 0 0 18px;">${items}</ul></div>`);
    }
    if (extraRows.length > 0) {
        extraHtml = `
            <div style="margin-top: 12px; padding: 12px 15px; background:var(--surface-soft); border-radius: 16px; text-align: left; font-size: 13px; color:var(--fg-strong); line-height: 1.6;">
                ${extraRows.join('')}
                <div style="margin-top:6px; font-size:11px; color:var(--fg-faint);">Данные: 2ГИС${extra.nearby && extra.nearby.length ? ', © участники OpenStreetMap' : ''}</div>
            </div>
        `;
    }

    let gigachatHtml = '';
    if (mcc.gigachat_explanation) {
        gigachatHtml += `
            <div style="margin-top: 15px; padding: 15px; background: rgba(60,200,100,0.1); border-radius: 16px; border-left: 4px solid #4CAF50; text-align: left;">
                <div style="font-weight: 600; color:var(--accent-text); margin-bottom: 8px;">
                    🤖 Объяснение ИИ (GigaChat)
                </div>
                <p style="color:var(--fg-strong); font-size: 14px; line-height: 1.5;">
                    ${escapeHtml(mcc.gigachat_explanation)}
                </p>
            </div>
        `;
    }
    if (mcc.gigachat_products && mcc.gigachat_products.length > 0) {
        gigachatHtml += `
            <div style="margin-top: 15px; padding: 15px; background: rgba(30,100,50,0.3); border-radius: 16px; text-align: left;">
                <div style="font-weight: 600; color:var(--accent-text); margin-bottom: 8px;">
                    💡 Рекомендованные продукты (GigaChat)
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                    ${mcc.gigachat_products.map(p =>
                        `<span style="background: rgba(60,200,100,0.2); padding: 4px 12px; border-radius: 20px; font-size: 13px; color:var(--accent-text); border: 1px solid rgba(80,255,120,0.3);">${escapeHtml(p)}</span>`
                    ).join('')}
                </div>
            </div>
        `;
    }

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
                ${extraHtml}
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
                ${gigachatHtml}
                <div style="display: flex; gap: 15px; justify-content: center; flex-wrap: wrap; margin-top: 20px;">
                    <button class="wrong-mcc-button" id="reportWrongMccBtn" onclick="reportWrongMCC()">
                        <span>🚫</span> Неверный МСС
                    </button>
                    <button class="recommendations-button" id="recommendationsBtn" onclick="showRecommendations()">
                        <span>📊</span> Рекомендации по продажам
                    </button>
                    <button class="recommendations-button" id="companyInfoBtn" onclick="showCompanyInfo()">
                        <span>🏛️</span> Информация из DaData
                    </button>
                    <button class="recommendations-button" id="partnersBtn" onclick="showPartners()">
                        <span>🤝</span> Партнёры рядом (500 м)
                    </button>
                </div>
            </div>
        </div>
    `;
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
                <div style="font-size: 14px; color:var(--fg-medium);">Торговая точка:</div>
                <div style="font-size: 18px; font-weight: 600; color:var(--accent-text);">${escapeHtml(businessName)}</div>
                <div style="font-size: 13px; color:var(--fg-faint); margin-top: 5px;">MCC: ${mccCode} — ${escapeHtml(mccName)}</div>
            </div>

            <div style="margin-bottom: 20px;">
                <div style="background: rgba(60,200,100,0.1); border-radius: 16px; padding: 15px; margin-bottom: 12px;">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                        <span style="font-size: 24px;">💰</span>
                        <span style="font-weight: 700; color:var(--accent-text);">POS-кредитование</span>
                    </div>
                    <p style="color:var(--fg-strong); font-size: 14px; line-height: 1.5; white-space: pre-line;">${recommendations.posCreditMessage}</p>
                </div>

                <div style="background: rgba(60,200,100,0.1); border-radius: 16px; padding: 15px; margin-bottom: 12px;">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                        <span style="font-size: 24px;">💬</span>
                        <span style="font-weight: 700; color:var(--accent-text);">СберЧаевые</span>
                    </div>
                    <p style="color:var(--fg-strong); font-size: 14px; line-height: 1.5; white-space: pre-line;">${recommendations.sberTipsMessage}</p>
                </div>

                <div style="background: linear-gradient(135deg, rgba(30,100,50,0.3), rgba(20,60,40,0.3)); border-radius: 16px; padding: 15px; border-left: 4px solid #4CAF50;">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                        <span style="font-size: 24px;">🎯</span>
                        <span style="font-weight: 700; color:var(--accent-text);">Продажная рекомендация</span>
                    </div>
                    <p style="color:var(--fg-strong); font-size: 14px; line-height: 1.5; white-space: pre-line;">${recommendations.generalMessage}</p>
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

// Поиск перспективных партнёров в радиусе 500 м
async function showPartners(refresh = false) {
    if (!currentMCCData || !currentGeo) {
        showToast('❌ Сначала найдите торговую точку', true);
        return;
    }
    const existing = document.getElementById('partnersModal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.id = 'partnersModal';
    modal.className = 'modal-overlay';
    modal.style.display = 'flex';
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 600px;">
            <div class="modal-header">
                <h2><span>🤝</span> Партнёры рядом</h2>
                <div class="modal-close" onclick="document.getElementById('partnersModal').remove()">✕</div>
            </div>
            <div id="partnersBody" style="color:var(--fg-strong); font-size:14px;">⏳ Ищем организации в радиусе 500 м и анализируем их…</div>
        </div>
    `;
    document.body.appendChild(modal);
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
    const body = modal.querySelector('#partnersBody');

    try {
        const response = await fetch('/find_partners', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lat: currentGeo.lat, lon: currentGeo.lon, org_id: currentGeo.org_id, address: currentGeo.address, refresh: refresh,
                org_name: currentMCCData.org_name,
                mcc_code: currentMCCData.mcc_code, mcc_name: currentMCCData.mcc_name
            })
        });
        const result = await response.json();
        if (!result.success) {
            body.textContent = result.error || 'Не удалось выполнить поиск.';
            return;
        }
        if (!result.partners || result.partners.length === 0) {
            body.textContent = `В радиусе ${result.radius} м подходящих организаций не найдено.`;
            return;
        }
        const cards = result.partners.map((p, i) => `
            <div style="padding:12px 14px; margin-bottom:10px; background:rgba(60,200,100,0.12); border-radius:14px; border-left:3px solid #4CAF50;">
                <div style="font-weight:700; color:var(--accent-text); font-size:15px;">${i + 1}. ${escapeHtml(p.name)}</div>
                <div style="font-size:12px; color:var(--fg-faint); margin-top:2px;">📍 ${escapeHtml(p.address)} · ${p.distance_m} м</div>
                <div style="font-size:12px; color:var(--fg-medium); margin-top:4px;">МСС ${escapeHtml(p.mcc_code)} — ${escapeHtml(p.mcc_name)}</div>
                <div style="margin-top:6px;">${(p.products || []).map(x => `<span class="rubric-tag">${escapeHtml(x)}</span>`).join('')}</div>
                <p style="margin:8px 0 0; font-size:13px; line-height:1.5; color:var(--fg-strong);">${escapeHtml(p.reason)}</p>
            </div>`).join('');
        const note = result.ai
            ? 'Отбор: расчёт по шести критериям и анализ GigaChat.'
            : 'GigaChat недоступен: показан отбор по расчёту.';
        body.innerHTML = `
            <div style="font-size:12px; color:var(--fg-faint); margin-bottom:10px;">Проанализировано организаций в радиусе ${result.radius} м: ${result.found}</div>
            ${cards}
            <div style="margin-top:8px; font-size:11px; color:var(--fg-faint);">${note} Данные: 2ГИС${result.cached_at ? ', ' + (result.cached ? 'сохранены ' : 'получены ') + escapeHtml(result.cached_at) : ''}.
                ${result.cached ? '<a href="#" id="partnersRefresh" style="color:var(--accent-text); margin-left:6px;">Обновить</a>' : ''}</div>`;
        const refreshLink = body.querySelector('#partnersRefresh');
        if (refreshLink) refreshLink.addEventListener('click', (e) => { e.preventDefault(); showPartners(true); });
    } catch (e) {
        body.textContent = 'Ошибка соединения с сервером. Повторите попытку.';
    }
}

// Информация о юридическом лице из DaData (ИНН используется только для поиска и не выводится)
function showCompanyInfo() {
    const existing = document.getElementById('companyInfoModal');
    if (existing) existing.remove();

    const { state, info } = currentCompany;
    const name = currentMCCData ? currentMCCData.org_name : '';
    let body = '';
    if (state === 'ok' && info) {
        const card = (e, accent) => {
            const meta = [e.form, e.status, e.okved ? 'ОКВЭД ' + e.okved : ''].filter(Boolean).map(escapeHtml).join(' · ');
            return `
            <div style="padding:10px 12px; margin-bottom:8px; background:${accent ? 'rgba(60,200,100,0.18)' : 'var(--surface-soft)'}; border-radius:12px; ${accent ? 'border-left:3px solid #4CAF50;' : ''}">
                <div style="font-weight:600; color:${accent ? 'var(--accent-text)' : 'var(--fg-strong)'}; font-size:14px;">${escapeHtml(e.name)}${e.branch ? ' <span style="font-weight:400; color:var(--fg-faint);">(филиал)</span>' : ''}</div>
                ${e.address ? `<div style="font-size:12px; color:var(--fg-faint); margin-top:2px;">📍 ${escapeHtml(e.address)}</div>` : ''}
                ${meta ? `<div style="font-size:13px; color:var(--fg-strong); margin-top:4px;">${meta}</div>` : ''}
            </div>`;
        };
        const atAddress = info.at_address || [];
        const others = info.others || [];
        body = `<div style="font-size:13px; font-weight:600; color:var(--accent-text); margin:4px 0 8px;">По адресу точки</div>` +
            (atAddress.length
                ? atAddress.map(e => card(e, true)).join('')
                : `<p style="font-size:13px; color:var(--fg-medium); margin:0 0 8px;">Совпадений по адресу нет.</p>`);
        if (others.length) {
            body += `<div style="font-size:13px; font-weight:600; color:var(--fg-strong); margin:14px 0 8px;">Другие точки и юридические лица с таким названием</div>` +
                others.map(e => card(e, false)).join('');
        }
    } else {
        const messages = {
            not_found: 'Юридическое лицо торговой точки однозначно определить не удалось, поэтому дополнительные сведения не запрашивались.',
            disabled: 'Источник не подключён: в настройках приложения не задан ключ DaData.',
            error: 'Источник временно недоступен. Повторите поиск позже.'
        };
        body = `<p style="color:var(--fg-strong); font-size:14px; line-height:1.5;">${messages[state] || messages.not_found}</p>`;
    }

    const modal = document.createElement('div');
    modal.id = 'companyInfoModal';
    modal.className = 'modal-overlay';
    modal.style.display = 'flex';
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 560px;">
            <div class="modal-header">
                <h2><span>🏛️</span> Информация из DaData</h2>
                <div class="modal-close" onclick="document.getElementById('companyInfoModal').remove()">✕</div>
            </div>
            <div style="margin-bottom: 15px; padding: 12px; background: rgba(60,200,100,0.15); border-radius: 16px;">
                <div style="font-size: 14px; color:var(--fg-medium);">Торговая точка:</div>
                <div style="font-size: 18px; font-weight: 600; color:var(--accent-text);">${escapeHtml(name)}</div>
            </div>
            ${body}
            <div style="margin-top:14px; font-size:11px; color:var(--fg-faint);">Источник: ЕГРЮЛ / ЕГРИП через DaData</div>
        </div>
    `;
    document.body.appendChild(modal);
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
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

// Выбор торговой точки на карте 2ГИС (MapGL JS API)
(function () {
    if (window.__mapPickerInit) return;  // защита от двойного подключения
    window.__mapPickerInit = true;
    const toggleBtn = document.getElementById('mapToggleBtn');
    const panel = document.getElementById('mapPanel');
    const resultsBox = document.getElementById('mapResults');
    if (!toggleBtn || !panel) return;

    let map = null;
    let marker = null;
    let loading = false;

    function loadMapgl() {
        return new Promise((resolve, reject) => {
            if (window.mapgl) return resolve();
            const script = document.createElement('script');
            script.src = 'https://mapgl.2gis.com/api/js/v1';
            script.async = true;
            script.onload = () => resolve();
            script.onerror = () => reject(new Error('скрипт не загрузился (сеть, блокировщик или доступ запрещён)'));
            setTimeout(() => reject(new Error('превышено время ожидания 15 секунд')), 15000);
            document.head.appendChild(script);
        });
    }

    function showMessage(text) {
        resultsBox.innerHTML = `<div style="font-size:13px; color:var(--fg-medium);">${escapeHtml(text)}</div>`;
    }

    function selectOrganization(org) {
        orgNameInput.value = org.name;
        addressInput.value = org.address;
        resultsBox.innerHTML = `<div style="font-size:13px; color:var(--accent-text);">✅ Выбрано: ${escapeHtml(org.name)}, ${escapeHtml(org.address)}. Нажмите «Найти и определить MCC».</div>`;
    }

    async function onMapClick(lngLat) {
        const [lon, lat] = lngLat;
        if (marker) marker.destroy();
        marker = new mapgl.Marker(map, { coordinates: [lon, lat] });
        showMessage('⏳ Ищем организации рядом…');
        try {
            const response = await fetch('/organizations_at_point', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lat, lon })
            });
            const data = await response.json();
            if (!data.success) return showMessage(data.error || 'Не удалось выполнить поиск.');
            if (!data.organizations.length) return showMessage('Рядом с этой точкой организаций не найдено. Кликните ближе к вывеске или входу.');
            resultsBox.innerHTML = '';
            data.organizations.forEach(org => {
                const row = document.createElement('div');
                row.style.cssText = 'padding:8px 12px; margin-bottom:6px; background:var(--surface-soft); border-radius:12px; cursor:pointer; font-size:13px;';
                row.innerHTML = `<b style="color:var(--accent-text);">${escapeHtml(org.name)}</b><div style="color:var(--fg-faint); font-size:12px;">${escapeHtml(org.address)}</div>`;
                row.addEventListener('click', () => selectOrganization(org));
                resultsBox.appendChild(row);
            });
        } catch (e) {
            showMessage('Ошибка соединения с сервером.');
        }
    }

    async function initMap() {
        if (map || loading) return;
        loading = true;
        showMessage('⏳ Загружаем карту…');
        let step = 'настройки карты';
        try {
            const configResponse = await fetch('/map_config');
            if (!configResponse.ok) throw new Error('сервер вернул ' + configResponse.status);
            const config = await configResponse.json();
            if (!config.key) {
                showMessage('Карта не настроена: в .env не задан ключ 2ГИС (DGIS_MAP_KEY или DGIS_API_KEY).');
                return;
            }
            step = 'скрипт mapgl.2gis.com';
            await loadMapgl();
            step = 'создание карты';
            const geo = (typeof currentGeo !== 'undefined' && currentGeo && currentGeo.lat != null)
                ? [currentGeo.lon, currentGeo.lat] : config.center;
            map = new mapgl.Map('mapContainer', { center: geo, zoom: config.zoom, key: config.key });
            step = 'обработчик клика';
            map.on('click', (e) => onMapClick(e.lngLat));
            showMessage('');
        } catch (e) {
            console.error('Карта: ошибка на шаге «' + step + '»:', e);
            const hints = {
                'скрипт mapgl.2gis.com': 'Браузер не смог загрузить https://mapgl.2gis.com/api/js/v1. Проверьте интернет, блокировщик рекламы и доступ к этому адресу (откройте его в новой вкладке: должен показаться программный код).',
                'создание карты': 'Скрипт загружен, но карта не создалась. Проверьте ключ в .env и права ключа на MapGL JS API.'
            };
            showMessage('Не удалось открыть карту на шаге «' + step + '»: ' + (e && e.message ? e.message : e) + '. ' + (hints[step] || ''));
            map = null;
        } finally {
            loading = false;
        }
    }

    toggleBtn.addEventListener('click', () => {
        const open = panel.style.display === 'none';
        panel.style.display = open ? 'block' : 'none';
        if (open) initMap();
    });
})();