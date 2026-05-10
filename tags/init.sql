-- =====================================================
-- Инициализация системы тегов для трекера привычек
-- С подсказками для пользователя
-- =====================================================

-- Очистка таблиц (с учётом зависимостей)
TRUNCATE TABLE tag_category_weights CASCADE;
TRUNCATE TABLE tags CASCADE;
TRUNCATE TABLE activity_types CASCADE;
TRUNCATE TABLE categories CASCADE;

-- 1. Категории (аналитические)
INSERT INTO categories (name) VALUES
('здоровье'),
('обучение'),
('продуктивность'),
('ментальное состояние'),
('личная жизнь');

-- 2. Типы активности (скрытые)
INSERT INTO activity_types (name) VALUES
('физическая'),
('когнитивная'),
('социальная'),
('бытовая'),
('восстановление'),
('творческая');

-- 3. Теги с подсказками
INSERT INTO tags (name, activity_type_id, hint) VALUES
-- Физические и спорт
('бег', (SELECT id FROM activity_types WHERE name='физическая'), '🏃 Бег на улице или дорожке. Хотя бы 10 минут.'),
('ходьба', (SELECT id FROM activity_types WHERE name='физическая'), '🚶 Прогулка пешком. Можно по пути на работу или отдельно.'),
('силовая тренировка', (SELECT id FROM activity_types WHERE name='физическая'), '🏋️‍♂️ Тренировка с весом: гантели, турник, брусья или тренажёры.'),
('кардио', (SELECT id FROM activity_types WHERE name='физическая'), '❤️ Велосипед, эллипс, скакалка — всё что поднимает пульс.'),
('растяжка', (SELECT id FROM activity_types WHERE name='физическая'), '🧘‍♀️ Стретчинг, гибкость. После тренировки или отдельно.'),
('йога', (SELECT id FROM activity_types WHERE name='восстановление'), '🧘‍♂️ Практика асан и дыхания. Успокаивает и укрепляет тело.'),
('зарядка', (SELECT id FROM activity_types WHERE name='физическая'), '☀️ Короткая утренняя разминка на 5-10 минут.'),

-- Восстановление и сон
('сон', (SELECT id FROM activity_types WHERE name='восстановление'), '😴 Полноценный ночной сон. Отмечай, если спал 7-8 часов.'),
('ранний сон', (SELECT id FROM activity_types WHERE name='восстановление'), '🌙 Лёг спать до 23:00. Помогает режиму.'),
('медитация', (SELECT id FROM activity_types WHERE name='восстановление'), '🧠 Сиди тихо и наблюдай за дыханием. Хотя бы 5 минут.'),
('отдых без экрана', (SELECT id FROM activity_types WHERE name='восстановление'), '📵 Час без телефона, TV и компа. Почитай книгу или просто полежи.'),
('природа / прогулка', (SELECT id FROM activity_types WHERE name='восстановление'), '🌲 Выход на улицу в парк/лес. Можно совмещать с ходьбой.'),

-- Питание
('здоровое питание', (SELECT id FROM activity_types WHERE name='бытовая'), '🥗 Сбалансированный приём пищи без фастфуда и сахара.'),
('вода', (SELECT id FROM activity_types WHERE name='бытовая'), '💧 Выпил стакан воды. Отмечай за каждый или за норму в день.'),
('готовка', (SELECT id FROM activity_types WHERE name='бытовая'), '🍳 Приготовил еду сам из цельных продуктов.'),

-- Обучение и когнитивное
('чтение (книги)', (SELECT id FROM activity_types WHERE name='когнитивная'), '📖 Чтение художественной или нон-фикшн книги. Не новости и не соцсети.'),
('чтение (статьи)', (SELECT id FROM activity_types WHERE name='когнитивная'), '📰 Чтение полезных статей, блогов, документации.'),
('онлайн-курс', (SELECT id FROM activity_types WHERE name='когнитивная'), '💻 Прохождение курса на Coursera, Stepik, Udemy и т.д.'),
('изучение языка', (SELECT id FROM activity_types WHERE name='когнитивная'), '🇬🇧 Слова, грамматика, разговорная практика.'),
('подкаст / видео', (SELECT id FROM activity_types WHERE name='когнитивная'), '🎧 Обучающий подкаст или видео (TED, лекции). Не развлекательное.'),

-- Работа и продуктивность
('deep work', (SELECT id FROM activity_types WHERE name='когнитивная'), '⚡ Фокусная работа без отвлечений на соцсети и почту.'),
('планирование', (SELECT id FROM activity_types WHERE name='когнитивная'), '📝 Составление плана на день/неделю.'),
('рабочие задачи', (SELECT id FROM activity_types WHERE name='когнитивная'), '💼 Выполнение обычных рабочих дел, не deep work.'),
('ограничение экрана', (SELECT id FROM activity_types WHERE name='когнитивная'), '⏲️ Сознательно провёл меньше времени в телефоне/ноутбуке.'),
('цифровой детокс', (SELECT id FROM activity_types WHERE name='восстановление'), '📴 Полный отказ от гаджетов на несколько часов или день.'),

-- Ментальное состояние
('дневник', (SELECT id FROM activity_types WHERE name='когнитивная'), '✍️ Записал мысли, эмоции или события дня.'),
('благодарность', (SELECT id FROM activity_types WHERE name='когнитивная'), '🙏 Написал 3 вещи, за которые благодарен сегодня.'),
('рефлексия', (SELECT id FROM activity_types WHERE name='когнитивная'), '🤔 Подумал о своём поведении, ошибках и выводах.'),
('дыхательная практика', (SELECT id FROM activity_types WHERE name='восстановление'), '🌬️ Осознанное дыхание по квадрату или 4-7-8.'),

-- Творчество
('рисование', (SELECT id FROM activity_types WHERE name='творческая'), '🎨 Карандаш, краски, цифровой рисунок — не важно.'),
('музыка', (SELECT id FROM activity_types WHERE name='творческая'), '🎵 Игра на инструменте, пение или сочинение музыки.'),
('письмо / блог', (SELECT id FROM activity_types WHERE name='творческая'), '✍️ Написание рассказа, стиха или поста в блог.'),

-- Социальное
('друзья (вживую)', (SELECT id FROM activity_types WHERE name='социальная'), '👥 Встреча с друзьями в реале. Кофе, прогулка, настолки.'),
('семья', (SELECT id FROM activity_types WHERE name='социальная'), '🏠 Время с родственниками (не бытовое, а общение).'),
('нетворкинг', (SELECT id FROM activity_types WHERE name='социальная'), '🤝 Общение с коллегами или профессионалами.'),
('общение (звонок)', (SELECT id FROM activity_types WHERE name='социальная'), '📞 Позвонил близкому человеку или видеозвонок.'),

-- Быт и финансы
('уборка', (SELECT id FROM activity_types WHERE name='бытовая'), '🧹 Помыл пол, протёр пыль, навёл порядок.'),
('покупки', (SELECT id FROM activity_types WHERE name='бытовая'), '🛒 Сходил за продуктами или нужными вещами по списку.'),
('бюджет / учёт денег', (SELECT id FROM activity_types WHERE name='когнитивная'), '💰 Записал расходы, составил бюджет или проверил счета.');

-- 4. Веса тегов по категориям (остаются без изменений, как в прошлом скрипте)
-- Здесь вставляем тот же блок INSERT INTO tag_category_weights ... (полный)
-- Для краткости я его опущу, но он должен быть полностью скопирован из предыдущего сообщения.
-- Только убедись, что в нём есть все 40+ тегов.

-- Проверка: вывести все теги с подсказками
SELECT 
    t.name AS tag,
    t.hint AS подсказка,
    at.name AS тип_активности
FROM tags t
JOIN activity_types at ON t.activity_type_id = at.id
ORDER BY t.name;

-- 4. Веса тегов по категориям (tag_id, category_id, weight)
INSERT INTO tag_category_weights (tag_id, category_id, weight) VALUES
-- бег
((SELECT id FROM tags WHERE name='бег'), (SELECT id FROM categories WHERE name='здоровье'), 0.8),
((SELECT id FROM tags WHERE name='бег'), (SELECT id FROM categories WHERE name='ментальное состояние'), 0.2),

-- ходьба
((SELECT id FROM tags WHERE name='ходьба'), (SELECT id FROM categories WHERE name='здоровье'), 0.7),
((SELECT id FROM tags WHERE name='ходьба'), (SELECT id FROM categories WHERE name='ментальное состояние'), 0.3),

-- силовая тренировка
((SELECT id FROM tags WHERE name='силовая тренировка'), (SELECT id FROM categories WHERE name='здоровье'), 0.9),
((SELECT id FROM tags WHERE name='силовая тренировка'), (SELECT id FROM categories WHERE name='продуктивность'), 0.1),

-- кардио
((SELECT id FROM tags WHERE name='кардио'), (SELECT id FROM categories WHERE name='здоровье'), 0.9),

-- растяжка
((SELECT id FROM tags WHERE name='растяжка'), (SELECT id FROM categories WHERE name='здоровье'), 0.6),
((SELECT id FROM tags WHERE name='растяжка'), (SELECT id FROM categories WHERE name='ментальное состояние'), 0.4),

-- йога
((SELECT id FROM tags WHERE name='йога'), (SELECT id FROM categories WHERE name='здоровье'), 0.4),
((SELECT id FROM tags WHERE name='йога'), (SELECT id FROM categories WHERE name='ментальное состояние'), 0.6),

-- зарядка
((SELECT id FROM tags WHERE name='зарядка'), (SELECT id FROM categories WHERE name='здоровье'), 0.8),
((SELECT id FROM tags WHERE name='зарядка'), (SELECT id FROM categories WHERE name='продуктивность'), 0.2),

-- сон
((SELECT id FROM tags WHERE name='сон'), (SELECT id FROM categories WHERE name='здоровье'), 0.7),
((SELECT id FROM tags WHERE name='сон'), (SELECT id FROM categories WHERE name='ментальное состояние'), 0.3),

-- ранний сон
((SELECT id FROM tags WHERE name='ранний сон'), (SELECT id FROM categories WHERE name='здоровье'), 0.8),
((SELECT id FROM tags WHERE name='ранний сон'), (SELECT id FROM categories WHERE name='продуктивность'), 0.2),

-- медитация
((SELECT id FROM tags WHERE name='медитация'), (SELECT id FROM categories WHERE name='ментальное состояние'), 0.9),
((SELECT id FROM tags WHERE name='медитация'), (SELECT id FROM categories WHERE name='личная жизнь'), 0.1),

-- отдых без экрана
((SELECT id FROM tags WHERE name='отдых без экрана'), (SELECT id FROM categories WHERE name='ментальное состояние'), 0.6),
((SELECT id FROM tags WHERE name='отдых без экрана'), (SELECT id FROM categories WHERE name='здоровье'), 0.4),

-- природа / прогулка
((SELECT id FROM tags WHERE name='природа / прогулка'), (SELECT id FROM categories WHERE name='ментальное состояние'), 0.7),
((SELECT id FROM tags WHERE name='природа / прогулка'), (SELECT id FROM categories WHERE name='здоровье'), 0.3),

-- здоровое питание
((SELECT id FROM tags WHERE name='здоровое питание'), (SELECT id FROM categories WHERE name='здоровье'), 0.9),
((SELECT id FROM tags WHERE name='здоровое питание'), (SELECT id FROM categories WHERE name='личная жизнь'), 0.1),

-- вода
((SELECT id FROM tags WHERE name='вода'), (SELECT id FROM categories WHERE name='здоровье'), 1.0),

-- готовка
((SELECT id FROM tags WHERE name='готовка'), (SELECT id FROM categories WHERE name='здоровье'), 0.5),
((SELECT id FROM tags WHERE name='готовка'), (SELECT id FROM categories WHERE name='личная жизнь'), 0.3),
((SELECT id FROM tags WHERE name='готовка'), (SELECT id FROM categories WHERE name='обучение'), 0.2),

-- чтение (книги)
((SELECT id FROM tags WHERE name='чтение (книги)'), (SELECT id FROM categories WHERE name='обучение'), 0.7),
((SELECT id FROM tags WHERE name='чтение (книги)'), (SELECT id FROM categories WHERE name='ментальное состояние'), 0.3),

-- чтение (статьи)
((SELECT id FROM tags WHERE name='чтение (статьи)'), (SELECT id FROM categories WHERE name='обучение'), 0.6),
((SELECT id FROM tags WHERE name='чтение (статьи)'), (SELECT id FROM categories WHERE name='продуктивность'), 0.4),

-- онлайн-курс
((SELECT id FROM tags WHERE name='онлайн-курс'), (SELECT id FROM categories WHERE name='обучение'), 0.9),
((SELECT id FROM tags WHERE name='онлайн-курс'), (SELECT id FROM categories WHERE name='продуктивность'), 0.1),

-- изучение языка
((SELECT id FROM tags WHERE name='изучение языка'), (SELECT id FROM categories WHERE name='обучение'), 1.0),

-- подкаст / видео
((SELECT id FROM tags WHERE name='подкаст / видео'), (SELECT id FROM categories WHERE name='обучение'), 0.8),
((SELECT id FROM tags WHERE name='подкаст / видео'), (SELECT id FROM categories WHERE name='продуктивность'), 0.2),

-- deep work
((SELECT id FROM tags WHERE name='deep work'), (SELECT id FROM categories WHERE name='продуктивность'), 0.9),
((SELECT id FROM tags WHERE name='deep work'), (SELECT id FROM categories WHERE name='обучение'), 0.1),

-- планирование
((SELECT id FROM tags WHERE name='планирование'), (SELECT id FROM categories WHERE name='продуктивность'), 0.7),
((SELECT id FROM tags WHERE name='планирование'), (SELECT id FROM categories WHERE name='ментальное состояние'), 0.3),

-- рабочие задачи
((SELECT id FROM tags WHERE name='рабочие задачи'), (SELECT id FROM categories WHERE name='продуктивность'), 0.8),
((SELECT id FROM tags WHERE name='рабочие задачи'), (SELECT id FROM categories WHERE name='личная жизнь'), 0.2),

-- ограничение экрана
((SELECT id FROM tags WHERE name='ограничение экрана'), (SELECT id FROM categories WHERE name='ментальное состояние'), 0.5),
((SELECT id FROM tags WHERE name='ограничение экрана'), (SELECT id FROM categories WHERE name='продуктивность'), 0.5),

-- цифровой детокс
((SELECT id FROM tags WHERE name='цифровой детокс'), (SELECT id FROM categories WHERE name='ментальное состояние'), 0.8),
((SELECT id FROM tags WHERE name='цифровой детокс'), (SELECT id FROM categories WHERE name='здоровье'), 0.2),

-- дневник
((SELECT id FROM tags WHERE name='дневник'), (SELECT id FROM categories WHERE name='ментальное состояние'), 0.9),
((SELECT id FROM tags WHERE name='дневник'), (SELECT id FROM categories WHERE name='обучение'), 0.1),

-- благодарность
((SELECT id FROM tags WHERE name='благодарность'), (SELECT id FROM categories WHERE name='ментальное состояние'), 1.0),

-- рефлексия
((SELECT id FROM tags WHERE name='рефлексия'), (SELECT id FROM categories WHERE name='ментальное состояние'), 0.8),
((SELECT id FROM tags WHERE name='рефлексия'), (SELECT id FROM categories WHERE name='обучение'), 0.2),

-- дыхательная практика
((SELECT id FROM tags WHERE name='дыхательная практика'), (SELECT id FROM categories WHERE name='ментальное состояние'), 0.9),

-- рисование
((SELECT id FROM tags WHERE name='рисование'), (SELECT id FROM categories WHERE name='ментальное состояние'), 0.5),
((SELECT id FROM tags WHERE name='рисование'), (SELECT id FROM categories WHERE name='обучение'), 0.5),

-- музыка
((SELECT id FROM tags WHERE name='музыка'), (SELECT id FROM categories WHERE name='ментальное состояние'), 0.6),
((SELECT id FROM tags WHERE name='музыка'), (SELECT id FROM categories WHERE name='обучение'), 0.4),

-- письмо / блог
((SELECT id FROM tags WHERE name='письмо / блог'), (SELECT id FROM categories WHERE name='ментальное состояние'), 0.5),
((SELECT id FROM tags WHERE name='письмо / блог'), (SELECT id FROM categories WHERE name='обучение'), 0.5),

-- друзья (вживую)
((SELECT id FROM tags WHERE name='друзья (вживую)'), (SELECT id FROM categories WHERE name='личная жизнь'), 0.8),
((SELECT id FROM tags WHERE name='друзья (вживую)'), (SELECT id FROM categories WHERE name='ментальное состояние'), 0.2),

-- семья
((SELECT id FROM tags WHERE name='семья'), (SELECT id FROM categories WHERE name='личная жизнь'), 0.9),
((SELECT id FROM tags WHERE name='семья'), (SELECT id FROM categories WHERE name='ментальное состояние'), 0.1),

-- нетворкинг
((SELECT id FROM tags WHERE name='нетворкинг'), (SELECT id FROM categories WHERE name='продуктивность'), 0.6),
((SELECT id FROM tags WHERE name='нетворкинг'), (SELECT id FROM categories WHERE name='личная жизнь'), 0.4),

-- общение (звонок)
((SELECT id FROM tags WHERE name='общение (звонок)'), (SELECT id FROM categories WHERE name='личная жизнь'), 0.7),
((SELECT id FROM tags WHERE name='общение (звонок)'), (SELECT id FROM categories WHERE name='ментальное состояние'), 0.3),

-- уборка
((SELECT id FROM tags WHERE name='уборка'), (SELECT id FROM categories WHERE name='личная жизнь'), 0.7),
((SELECT id FROM tags WHERE name='уборка'), (SELECT id FROM categories WHERE name='продуктивность'), 0.3),

-- покупки
((SELECT id FROM tags WHERE name='покупки'), (SELECT id FROM categories WHERE name='личная жизнь'), 0.6),
((SELECT id FROM tags WHERE name='покупки'), (SELECT id FROM categories WHERE name='продуктивность'), 0.4),

-- бюджет / учёт денег
((SELECT id FROM tags WHERE name='бюджет / учёт денег'), (SELECT id FROM categories WHERE name='продуктивность'), 0.6),
((SELECT id FROM tags WHERE name='бюджет / учёт денег'), (SELECT id FROM categories WHERE name='личная жизнь'), 0.4);

-- Проверка: вывести все теги с их весами (опционально)
SELECT 
    t.name AS tag_name,
    at.name AS activity_type,
    c.name AS category_name,
    tcw.weight
FROM tags t
JOIN activity_types at ON t.activity_type_id = at.id
JOIN tag_category_weights tcw ON t.id = tcw.tag_id
JOIN categories c ON tcw.category_id = c.id
ORDER BY t.name, c.name;