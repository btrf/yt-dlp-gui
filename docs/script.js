(function () {
    'use strict';

    var APP_VERSION = '2.0.3';
    var LANG_STORAGE_KEY = 'yt-dlp-gui-lang';
    var DEFAULT_LANG = 'ru';
    var SUPPORTED_LANGS = ['ru', 'en'];

    var HTML_KEYS = {
        feature_filename_text: true,
        feature_batch_text: true,
        step_1: true,
        step_2: true,
        step_3: true,
        install_note: true
    };

    var I18N = {
        ru: {
            meta_description: 'yt-dlp GUI — лёгкое портативное приложение для Windows: скачивание видео и аудио с сайтов, поддержка плейлистов, выбор качества и формата, пакетная загрузка. Без установки.',
            hero_badge: 'Портативное приложение для Windows',
            hero_title: 'Скачивайте видео и аудио без лишних усилий',
            hero_lead: 'yt-dlp GUI — лёгкая графическая обёртка над yt-dlp. Один файл, никакой установки: запустил, вставил ссылку, получил файл.',
            cta_download: 'Скачать для Windows',
            cta_secondary: 'Как установить',
            fact_no_install: 'Без установки',
            fact_single_file: 'Один файл',
            fact_free: 'Бесплатно',
            fact_offline_ready: 'Готов к работе сразу',
            hero_image_alt: 'yt-dlp GUI',
            demo_title: 'Демонстрация',
            demo_lead: 'Загрузка из списка ссылок, прогресс и итог — всё в одном окне.',
            demo_image_alt: 'Демонстрация работы yt-dlp GUI',
            features_title: 'Возможности',
            features_lead: 'Всё, что нужно для загрузки видео и аудио, — и ничего лишнего.',
            feature_sites_title: 'Сайты, которые поддерживает yt-dlp',
            feature_sites_text: 'YouTube, VK, OK, Twitter/X, TikTok, Instagram*, Dailymotion, Reddit и тысячи других — покрытие целиком берётся от yt-dlp.',
            feature_media_title: 'Видео и аудио',
            feature_media_text: 'Сохраняйте полноценные видеоролики или извлекайте звук в MP3/M4A.',
            feature_quality_title: 'Качество и формат',
            feature_quality_text: 'Выберите пресет качества (до 4K), ограничьте разрешение по высоте или задайте конкретный формат.',
            feature_playlists_title: 'Плейлисты',
            feature_playlists_text: 'Скачивайте плейлист целиком, только первый или последний ролик, диапазон «2:5» или выбранные элементы «1,3,5».',
            feature_filename_title: 'Шаблон имени файла',
            feature_filename_text: 'Задайте свой шаблон, например <code>%(title)s [%(id)s].%(ext)s</code>, и сохраняйте файлы так, как удобно.',
            feature_extra_title: 'Дополнительные аргументы',
            feature_extra_text: 'Пробросьте любые флаги yt-dlp вручную, если нужно нестандартное поведение.',
            feature_batch_title: 'Пакетная загрузка из файла',
            feature_batch_text: 'Импортируйте <code>.txt</code>-список ссылок — приложение скачает их по очереди в одном запуске.',
            feature_config_title: 'Запоминание настроек',
            feature_config_text: 'Выбор качества, шаблон имени и дополнительные аргументы сохраняются между запусками.',
            nav_features: 'Возможности',
            nav_install: 'Установка',
            nav_usage: 'Использование',
            nav_support: 'Поддержка',
            install_title: 'Установка и запуск',
            install_lead: 'Установка не требуется — приложение работает одним файлом.',
            step_1: 'Скачайте <code>yt-dlp-gui-portable-v2.0.3.exe</code> со страницы релизов.',
            step_2: 'Сохраните файл в любую папку — например, в <code>C:\\yt-dlp-gui\\</code>.',
            step_3: 'Запустите <code>.exe</code>. Windows может показать предупреждение SmartScreen — нажмите «Подробнее» → «Выполнить в любом случае».',
            step_4: 'Вставьте ссылку на видео или импортируйте список ссылок из файла и нажмите «Скачать».',
            install_note: 'Нужен только <code>ffmpeg</code> для объединения дорожек и конвертации звука — он входит в сборку или устанавливается отдельно.',
            cta_download_again: 'Перейти к загрузке',
            usage_title: 'Как пользоваться',
            usage_lead: 'Четыре шага — и файл у вас на диске.',
            usage_step_1_title: 'Вставьте ссылку',
            usage_step_1_text: 'Скопируйте адрес страницы с видео и вставьте его в поле Source.',
            usage_step_2_title: 'Выберите параметры',
            usage_step_2_text: 'Тип (видео/аудио), качество, формат, шаблон имени и дополнительные аргументы.',
            usage_step_3_title: 'Запустите загрузку',
            usage_step_3_text: 'Нажмите «Скачать» — прогресс отображается в реальном времени.',
            usage_step_4_title: 'Заберите файл',
            usage_step_4_text: 'Готовый файл окажется в папке Downloads или там, куда вы его направите.',
            options_title: 'Плейлисты и список ссылок',
            options_text: 'Отметьте «Скачать плейлист», чтобы включить выбор области: весь список, первый или последний элемент, диапазон или конкретные номера. Кнопка импорта принимает обычный текстовый файл со ссылками — каждая строка обрабатывается по очереди.',
            support_title: 'Поддержать проект',
            support_lead: 'Проект бесплатный и с открытым кодом. Если он оказался полезным, можно поддержать его донатом.',
            cta_donate: 'Поддержать на Ko-fi',
            cta_issues: 'Сообщить о проблеме',
            support_image_alt: 'QR-код для поддержки проекта',
            support_qr_caption: 'Отсканируйте QR-код',
            footer_source: 'Исходный код',
            footer_releases: 'Релизы',
            footer_issues: 'Проблемы'
        },
        en: {
            meta_description: 'yt-dlp GUI — a lightweight portable app for Windows: download video and audio from websites, playlist support, quality and format selection, batch downloads. No installation.',
            hero_badge: 'Portable app for Windows',
            hero_title: 'Download video and audio without any hassle',
            hero_lead: 'yt-dlp GUI — a lightweight graphical wrapper for yt-dlp. No installation, just one file: run it, paste a link, get the file.',
            cta_download: 'Download for Windows',
            cta_secondary: 'How to install',
            fact_no_install: 'No install',
            fact_single_file: 'Single file',
            fact_free: 'Free',
            fact_offline_ready: 'Works right away',
            hero_image_alt: 'yt-dlp GUI',
            demo_title: 'Demo',
            demo_lead: 'Downloading from a list of links, progress and the result — all in one window.',
            demo_image_alt: 'yt-dlp GUI in action',
            features_title: 'Features',
            features_lead: 'Everything you need to download video and audio — and nothing extra.',
            feature_sites_title: 'Sites supported by yt-dlp',
            feature_sites_text: 'YouTube, VK, OK, Twitter/X, TikTok, Instagram*, Dailymotion, Reddit and thousands more — full coverage inherited from yt-dlp.',
            feature_media_title: 'Video and audio',
            feature_media_text: 'Save full videos or extract the sound as MP3/M4A.',
            feature_quality_title: 'Quality and format',
            feature_quality_text: 'Pick a quality preset (up to 4K), cap the height resolution or set a specific format.',
            feature_playlists_title: 'Playlists',
            feature_playlists_text: 'Download a whole playlist, only the first or last item, a range like "2:5" or selected items "1,3,5".',
            feature_filename_title: 'Filename template',
            feature_filename_text: 'Set your own template, e.g. <code>%(title)s [%(id)s].%(ext)s</code>, and keep files the way you want.',
            feature_extra_title: 'Extra arguments',
            feature_extra_text: 'Pass any yt-dlp flags manually if you need non-standard behaviour.',
            feature_batch_title: 'Batch download from file',
            feature_batch_text: 'Import a <code>.txt</code> list of links — the app downloads them one by one in a single run.',
            feature_config_title: 'Remembers your settings',
            feature_config_text: 'Quality choice, filename template and extra arguments are kept between launches.',
            nav_features: 'Features',
            nav_install: 'Install',
            nav_usage: 'Usage',
            nav_support: 'Support',
            install_title: 'Installation and launch',
            install_lead: 'No installation required — the app runs as a single file.',
            step_1: 'Download <code>yt-dlp-gui-portable-v2.0.3.exe</code> from the releases page.',
            step_2: 'Save the file into any folder — for example <code>C:\\yt-dlp-gui\\</code>.',
            step_3: 'Run the <code>.exe</code>. Windows may show a SmartScreen warning — click "More info" then "Run anyway".',
            step_4: 'Paste a video link or import a link list from a file and press "Download".',
            install_note: 'You only need <code>ffmpeg</code> to merge tracks and convert audio — it is bundled or installed separately.',
            cta_download_again: 'Go to downloads',
            usage_title: 'How to use',
            usage_lead: 'Four steps — and the file is on your disk.',
            usage_step_1_title: 'Paste a link',
            usage_step_1_text: 'Copy the address of the page with the video and paste it into the Source field.',
            usage_step_2_title: 'Choose options',
            usage_step_2_text: 'Type (video/audio), quality, format, filename template and extra arguments.',
            usage_step_3_title: 'Start the download',
            usage_step_3_text: 'Press "Download" — progress updates in real time.',
            usage_step_4_title: 'Grab the file',
            usage_step_4_text: 'The finished file lands in the Downloads folder or wherever you pointed it.',
            options_title: 'Playlists and link lists',
            options_text: 'Tick "Download playlist" to enable scope selection: the whole list, the first or last item, a range or specific numbers. The import button accepts a plain text file with links — every line is processed in order.',
            support_title: 'Support the project',
            support_lead: 'The project is free and open source. If you find it useful, you can support it with a donation.',
            cta_donate: 'Support on Ko-fi',
            cta_issues: 'Report an issue',
            support_image_alt: 'QR code to support the project',
            support_qr_caption: 'Scan the QR code',
            footer_source: 'Source code',
            footer_releases: 'Releases',
            footer_issues: 'Issues'
        }
    };

    function applyLanguage(lang) {
        if (SUPPORTED_LANGS.indexOf(lang) === -1) {
            lang = DEFAULT_LANG;
        }

        var dict = I18N[lang];

        var textNodes = document.querySelectorAll('[data-i18n]');
        for (var i = 0; i < textNodes.length; i++) {
            var el = textNodes[i];
            var key = el.getAttribute('data-i18n');
            var value = dict[key];
            if (value === undefined) {
                continue;
            }
            if (HTML_KEYS[key]) {
                el.innerHTML = value;
            } else {
                el.textContent = value;
            }
        }

        var contentNodes = document.querySelectorAll('[data-i18n-content]');
        for (var j = 0; j < contentNodes.length; j++) {
            var meta = contentNodes[j];
            var contentKey = meta.getAttribute('data-i18n-content');
            if (dict[contentKey] !== undefined) {
                meta.setAttribute('content', dict[contentKey]);
            }
        }

        var altNodes = document.querySelectorAll('[data-i18n-alt]');
        for (var k = 0; k < altNodes.length; k++) {
            var img = altNodes[k];
            var altKey = img.getAttribute('data-i18n-alt');
            if (dict[altKey] !== undefined) {
                img.setAttribute('alt', dict[altKey]);
            }
        }

        var versionEl = document.getElementById('app-version');
        if (versionEl) {
            versionEl.textContent = APP_VERSION;
        }

        var toggleItems = document.querySelectorAll('.lang-toggle__item');
        for (var t = 0; t < toggleItems.length; t++) {
            if (toggleItems[t].getAttribute('data-lang') === lang) {
                toggleItems[t].classList.add('is-active');
            } else {
                toggleItems[t].classList.remove('is-active');
            }
        }

        document.documentElement.setAttribute('lang', lang);
    }

    function setLanguage(lang) {
        if (SUPPORTED_LANGS.indexOf(lang) === -1) {
            return;
        }
        try {
            window.localStorage.setItem(LANG_STORAGE_KEY, lang);
        } catch (ignore) {
        }
        applyLanguage(lang);
    }

    if (typeof document !== 'undefined') {
        var toggleItems = document.querySelectorAll('.lang-toggle__item[data-lang]');
        for (var n = 0; n < toggleItems.length; n++) {
            (function (item) {
                item.addEventListener('click', function () {
                    setLanguage(item.getAttribute('data-lang'));
                });
            })(toggleItems[n]);
        }

        var stored = null;
        try {
            stored = window.localStorage.getItem(LANG_STORAGE_KEY);
        } catch (ignore) {
            stored = null;
        }

        applyLanguage(SUPPORTED_LANGS.indexOf(stored) !== -1 ? stored : DEFAULT_LANG);
    }
})();