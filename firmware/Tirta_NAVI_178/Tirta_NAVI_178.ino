// Original Tirta/Kochetkov driver + AVCLanNavi module, GPLv3.
// Bench wrapper only: no EEPROM defaults, CDC app, raw pin commands or bus reset.
#include <Arduino.h>
#include "AVCLanDrv.h"
#include "AVCLanNavi.h"
#include "BuffSerial.h"
#include "BenchPins.h"
#include "BenchLanCheck.h"
#include "BenchCommunication.h"
#include "BenchAnnounce.h"
#include "NaviProfile.h"
#include "Cy12Application.h"
bool navi_b2_advertised=true;
bool tirtaActive=false;
static byte announceRemaining=0;
static uint32_t nextAnnounce=0;
static bool autoStartPending=true;
static bool fmKeyReleasePending=false;
static uint32_t fmKeyReleaseAt=0;
static void startEmulator(){
  if(tirtaActive)return;
  autoStartPending=false;
  cy12PingLast=0xff;cy12PingFirst=true;
  cy12VideoActive=false;cy12ModeFlag=false;cy12MapHeld=false;cy12MasterLogical=0x12;cy12Head03Seen=false;
  tirtaActive=true;avclan.readonly=false;
  bSerial.println_p(PSTR("ACTIVE_STARTED TIRTA_NAVI; until_STOP_or_reset"));
  // V850 FUN_00017538 sends CMD13 first, then schedules three 1 s retries.
  // Keep the existing Tirta PHY and the bench's observed logical master 12.
  announceRemaining=4;nextAnnounce=millis();
}
void setup(){
  tirtaRelease();bSerial.begin(250000);avclan.begin();avclanDevice.begin();
  avclan.readonly=true;
  // Head address was measured in this bench's valid bidirectional captures.
  avclan.headAddress=0x120;
  bSerial.print_p(PSTR("TIRTA_NAVI: profile=" NAVI_BENCH_PROFILE " ADDR="));
  bSerial.printHex4(avclan.deviceAddress>>8);bSerial.printHex8(avclan.deviceAddress);
  bSerial.print_p(PSTR(" HU=120 UART=250000 16MHz ACK_US="));
  bSerial.printDec(AVC_BIT_0_HOLD_ON_MIN_LENGTH/2);bSerial.println();
  bSerial.println_p(PSTR("TIRTA_FUNCTIONS=" NAVI_FUNCTION_HEX "; AUTO_START=1660ms; GO=CMD13; STOP=passive_until_reset"));
  bSerial.println_p(PSTR("TIRTA_ADDONS=Mock_LAN,CY12_CMD12,Mock_ping,CY12_DIAG"));
  bSerial.println_p(PSTR("TIRTA_UART_BUFFER=768; ANN=initiative_CMD13"));
}
void loop(){
  static char command[8];static byte n=0;
  while(bSerial.rxEnabled()){
    char c=bSerial.rxRead();
    if(c=='\n'){
      command[n]=0;n=0;
      if(!strcmp(command,"GO")){
        if(tirtaActive){bSerial.println_p(PSTR("TIRTA_ALREADY_ACTIVE"));continue;}
        startEmulator();
      }else if(!strcmp(command,"STOP")){
        autoStartPending=false;tirtaActive=false;avclan.readonly=true;cy12VideoActive=false;cy12ModeFlag=false;cy12MapHeld=false;announceRemaining=0;fmKeyReleasePending=false;tirtaRelease();
        bSerial.println_p(PSTR("STOPPED no_further_TX"));
      }else if((!strcmp(command,"P0") || !strcmp(command,"P1")) && tirtaActive){
        navi_b2_advertised=(command[1]=='1');
        cy12Head03Seen=false;
        announceRemaining=4;nextAnnounce=millis();
        bSerial.println_p(navi_b2_advertised ? PSTR("PROFILE_FULL requested") : PSTR("PROFILE_NO_B2 requested"));
      }else if(!strcmp(command,"ANN") && tirtaActive){
        benchAnnounce(cy12MasterLogical);
      }else if(!strcmp(command,"DSP") && tirtaActive){
        cy12RequestDisplay();
      }else if(!strcmp(command,"AUD1") && tirtaActive){
        cy12RequestAudio(true);
      }else if(!strcmp(command,"AUD0") && tirtaActive){
        cy12RequestAudio(false);
      }else if(tirtaActive && !fmKeyReleasePending &&
               (!strcmp(command,"AM") || !strcmp(command,"FM") || !strcmp(command,"CD") ||
                !strcmp(command,"AUX") || !strcmp(command,"XM") || !strcmp(command,"VTR") || !strcmp(command,"DAB"))){
        byte slot=2,mask=0;
        if(!strcmp(command,"AM"))mask=0x80;
        else if(!strcmp(command,"FM"))mask=0x40;
        else if(!strcmp(command,"CD"))mask=0x02;
        else if(!strcmp(command,"AUX")){slot=10;mask=0x08;}
        else if(!strcmp(command,"XM")){slot=10;mask=0x02;}
        else if(!strcmp(command,"VTR")){slot=11;mask=0x02;}
        else {slot=11;mask=0x01;}
        cy12HeadSourceKey(slot,mask,true);
        fmKeyReleasePending=true;fmKeyReleaseAt=millis()+150;
      }else if(!strcmp(command,"RGB0") && tirtaActive){
        cy12RgbStatus(false);
      }else if(!strcmp(command,"RGB1") && tirtaActive){
        cy12RgbStatus(true);
#if NAVI_HAS_LEGACY_6D
      }else if(!strcmp(command,"LEGACY") && tirtaActive){
        bSerial.println_p(PSTR("LEGACY_STATUS once; original_Tirta_CmdInit; CY11_unverified"));
        avclan.sendMessage(&CmdInit);
#endif
      }
    }else if(c!='\r'){if(n<sizeof(command)-1)command[n++]=c;else n=0;}
  }
  if(autoStartPending && millis()>=1660)startEmulator();
  if(tirtaActive && fmKeyReleasePending && (int32_t)(millis()-fmKeyReleaseAt)>=0 && !INPUT_IS_SET){
    fmKeyReleasePending=false;cy12HeadSourceKey(0,0,false);
  }
  if(INPUT_IS_SET){
    byte result=avclan.readMessage();
    // In the V850 state machine a master CMD00 also ends discovery: it
    // answers with CMD10 and changes state. Let the existing handler send it.
    if(!result && tirtaActive && avclan.masterAddress==avclan.headAddress &&
       avclan.control==0xF && avclan.broadcast==AVC_MSG_BROADCAST &&
       (avclan.slaveAddress==0xFFF || avclan.slaveAddress==0x1FF) &&
       avclan.dataSize==3 && avclan.message[0]==0x12 &&
       avclan.message[1]==1 && avclan.message[2]==0){
      announceRemaining=0;
      bSerial.println_p(PSTR("DISCOVERY_STOP master_CMD00"));
    }
    if(!result && tirtaActive && !cy12Handle() && !benchLanCheck() && !benchCommunication()){
      avclanDevice.getActionID();
      if(avclan.actionID!=ACT_NONE)avclanDevice.processAction((AvcActionID)avclan.actionID);
    }
  }
  if(tirtaActive && !cy12Head03Seen && announceRemaining &&
     (int32_t)(millis()-nextAnnounce)>=0 && !INPUT_IS_SET){
    benchAnnounce(cy12MasterLogical);--announceRemaining;nextAnnounce=millis()+1000;
  }
  if(tirtaActive && avclan.event!=EV_NONE){avclanDevice.processEvent((AvcEventID)avclan.event);avclan.event=EV_NONE;}
  static uint16_t reportedOverflow=0;static uint32_t overflowAt=0;
  if(bSerial.txOverflow!=reportedOverflow && (uint32_t)(millis()-overflowAt)>=1000){
    overflowAt=millis();reportedOverflow=bSerial.txOverflow;
    bSerial.print("TIRTA_UART_DROPPED_HEX=");bSerial.printHex8(reportedOverflow>>8);bSerial.printHex8(reportedOverflow);bSerial.println();
  }
}
