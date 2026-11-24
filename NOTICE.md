# Происхождение прошивки

Это стендовая адаптация к Toyota Touch TAS300. В ноябре 2026 года для неё использованы раздельные выводы приёма и передачи Nano, профиль адреса 0x122, регистрация внешнего модуля, обработка команд экрана и выбор источников. Текст GPLv3 включён вместе с прошивкой. Уведомления авторов в исходных файлах сохранены. [Лицензия](LICENSE)

| Компонент | Источник |
|---|---|
| Драйвер AVC-LAN и модуль NAVI, исходный автор Aleksey Kochetkov | [Tirta01/Arduino-AVCLan](https://github.com/Tirta01/Arduino-AVCLan), дерево `c2163b6bf11a00e18cae2f5a3516d991ce30b86f` |
| Обработчик проверки связи в `BenchLanCheck.h`, Allen Hill, GPL-3.0-or-later | [AVCLAN-Mockingboard](https://github.com/halleysfifthinc/AVCLAN-Mockingboard), дерево `6c460aa3a06f0effa2972b91d6a793a5cfbb7fa4`, файл `src/avclan/peripheral.hpp` |
| Справочный формат команды CMD12 | [GadgetNutt/AVC-LAN-Module-Builder](https://github.com/GadgetNutt/AVC-LAN-Module-Builder), дерево `208f4f13040942d0cbff53f6164573ea2c9107c2` |
| Ядро Arduino, с которым скомпонован AVR-образ | [ArduinoCore-avr 1.8.8](https://github.com/arduino/ArduinoCore-avr/tree/1.8.8). Заголовки компонентов ядра указывают их авторов и лицензии, в том числе LGPL-2.1-or-later для `main.cpp` и `wiring.c`. |
| Библиотека C в составе пакета компилятора AVR | [Исходники avr-libc 2.0.0](https://github.com/avrdudes/avr-libc/tree/avr-libc-2_0_0-release) и [уведомления об авторстве и условиях использования](licenses/avr-libc-2.0.0.txt) |

Текст лицензии основных файлов ядра Arduino приложен отдельно. [GNU LGPL 2.1](licenses/LGPL-2.1.txt)

Параметры RGBHV переписаны из конфигурации штатного блока и сопоставлены с измерениями стенда. Подробности и имена первичных файлов указаны в [документации по видео](docs/rgbhv.md).
