#pragma once
#include <Arduino.h>
#if !defined(__AVR_ATmega328P__) || F_CPU!=16000000UL
#error Requires Nano ATmega328P 16 MHz
#endif
extern bool tirtaActive;
static inline void tirtaRelease(){DDRD&=~(_BV(PD2)|_BV(PD3));PORTD&=~(_BV(PD2)|_BV(PD3));}
static inline void tirtaDrive(){if(!tirtaActive)return;PORTD=(PORTD|_BV(PD3))&~_BV(PD2);DDRD|=_BV(PD2)|_BV(PD3);}
