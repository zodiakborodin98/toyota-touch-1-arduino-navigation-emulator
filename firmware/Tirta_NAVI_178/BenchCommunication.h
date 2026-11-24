// Supplements the missing ACT_INIT/Ping handlers of Tirta AVCLanNavi 0.0.1.
// CMD12 framing: GadgetNutt; requested function list: CY12 V850 firmware.
// Ping reply order: AVCLAN-Mockingboard peripheral.hpp, Ping_Req branch.
// No new PHY/framing implementation. No NAVI-ready or RGB-status fabrication.
#pragma once
#include "AVCLanDrv.h"
#include "BuffSerial.h"
// V850 FUN_00017704: first token is accepted; afterwards a token must be
// the successor of the previous token, modulo 256. Status is 00 or FF.
static byte cy12PingLast=0xff;
static bool cy12PingFirst=true;
static bool benchCommunication(){
  if(avclan.masterAddress!=avclan.headAddress || avclan.control!=0xF)return false;
  const bool direct=avclan.broadcast==AVC_MSG_DIRECT;
  const byte at=direct?1:0;
  if(avclan.dataSize<at+3)return false;
  if(direct){if(avclan.slaveAddress!=avclan.deviceAddress || avclan.message[0])return false;}
  else if(avclan.slaveAddress!=0xFFF && avclan.slaveAddress!=0x1FF)return false;
  const byte from=avclan.message[at], to=avclan.message[at+1], cmd=avclan.message[at+2];
  if((from!=0x11 && from!=0x12) || to!=0x01)return false;
  if(cmd==0x02 && direct && avclan.dataSize>=4 && !((avclan.dataSize-4)&1)){
    bSerial.println("INIT_MAPPING_RECEIVED; NAVI_ready_not_assumed");return true;
  }
  if(cmd==0x03 && direct && avclan.dataSize==4){
    bSerial.println("HEAD_IDENTIFIED; NAVI_ready_not_assumed");return true;
  }
  const bool init=cmd==0x01 && avclan.dataSize==at+3;
  const bool ping=cmd==0x20 && avclan.dataSize==at+4;
  if(!init && !ping)return false;
  const byte token=ping?avclan.message[at+3]:0;
  if(init)bSerial.println_p(PSTR("COMM_INIT CMD12_from_CY12_firmware"));
  else bSerial.println_p(PSTR("COMM_PING CMD30_from_CY12_V850"));
  avclan.broadcast=AVC_MSG_DIRECT;avclan.masterAddress=avclan.deviceAddress;avclan.slaveAddress=avclan.headAddress;
  avclan.message[0]=0;avclan.message[1]=1;avclan.message[2]=from;
  if(init){
    // Exact 10-function discovery list in teb.bin (ROM offset 0x107c6).
    static const byte wanted[] PROGMEM={0x60,0x62,0x6F,0x41,0xC0,0xC4,0x74,0xA4,0x29,0x00};
    avclan.message[3]=0x12;avclan.dataSize=4+sizeof(wanted);
    memcpy_P(avclan.message+4,wanted,sizeof(wanted));
  }else{
    const byte status=(cy12PingFirst || byte(cy12PingLast+1)==token)?0:0xFF;
    cy12PingFirst=false;cy12PingLast=token;
    avclan.message[3]=0x30;avclan.message[4]=token;avclan.message[5]=status;avclan.dataSize=6;
  }
  avclan.sendMessage();return true;
}
