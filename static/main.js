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
cancelFeedback.addEventListener('click', closeFeedbackModal);

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

                <div style="text-align: center; margin-top: 20px;">
                    <button class="wrong-mcc-button" id="reportWrongMccBtn" onclick="reportWrongMCC()">
                        <span>🚫</span> Неверный МСС
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