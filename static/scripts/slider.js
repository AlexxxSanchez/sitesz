document.addEventListener('DOMContentLoaded', function () {
    const blocksPerSlide = 4; // Количество блоков на один слайд (2 строки по 4 блока)

    // Функция инициализации слайдера
    function initializeSlider(sliderId) {
        const itemsContainer = document.getElementById(`${sliderId}-items`);
        const indicatorContainer = document.getElementById(`${sliderId}-indicators`);
        const prevButton = document.querySelector(`.itc-slider-btn-prev[data-slider-id="${sliderId}"]`);
        const nextButton = document.querySelector(`.itc-slider-btn-next[data-slider-id="${sliderId}"]`);
        let currentIndex = 0;
        const slides = [];

        // Разбиваем блоки на слайды
        const blocks = Array.from(itemsContainer.children);
        for (let i = 0; i < blocks.length; i += blocksPerSlide) {
            const slide = document.createElement('div');
            slide.classList.add('itc-slider-item');

            const blockCenter = document.createElement('div');
            blockCenter.classList.add('block-center');

            const blockGrid = document.createElement('div');
            blockGrid.classList.add('block-grid');

            blocks.slice(i, i + blocksPerSlide).forEach(block => blockGrid.appendChild(block));

            blockCenter.appendChild(blockGrid);
            slide.appendChild(blockCenter);
            slides.push(slide);
        }

        // Очищаем контейнер и добавляем слайды
        itemsContainer.innerHTML = '';
        slides.forEach(slide => itemsContainer.appendChild(slide));

        // Добавляем индикаторы
        indicatorContainer.innerHTML = '';
        for (let i = 0; i < slides.length; i++) {
            const indicator = document.createElement('li');
            indicator.classList.add('itc-slider-indicator');
            indicator.dataset.slideTo = i;
            indicator.addEventListener('click', () => goToSlide(i));
            indicatorContainer.appendChild(indicator);
        }

        function updateIndicators() {
            const indicators = Array.from(indicatorContainer.children);
            indicators.forEach((indicator, index) => {
                indicator.classList.toggle('itc-slider-indicator-active', index === currentIndex);
            });
        }

        function goToSlide(index) {
            if (index < 0) {
                currentIndex = slides.length - 1;
            } else if (index >= slides.length) {
                currentIndex = 0;
            } else {
                currentIndex = index;
            }
            const offset = -currentIndex * 100;
            itemsContainer.style.transform = `translateX(${offset}%)`;
            updateIndicators();
        }

        prevButton.addEventListener('click', () => goToSlide(currentIndex - 1));
        nextButton.addEventListener('click', () => goToSlide(currentIndex + 1));

        // Инициализация первого слайда и индикатора
        goToSlide(0);
    }

    // Инициализация всех слайдеров на странице
    const sliders = document.querySelectorAll('.itc-slider');
    sliders.forEach(slider => {
        const sliderId = slider.id;
        initializeSlider(sliderId);
    });
});


