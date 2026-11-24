// LAN-check replies adapted from AVCLAN-Mockingboard, src/avclan/peripheral.hpp.
// Copyright (C) 2026 Allen Hill; SPDX-License-Identifier: GPL-3.0-or-later
// Upstream source: src/avclan/peripheral.hpp, Git blob 1113f3e2d593f14460bedd85a169ad55ddd41721 (see NOTICE.md).
// Upstream handles broadcast LAN checks. This bench also accepts the same
// logical request in the addressed envelope actually captured from this HU.
// Transport, physical ACK and bit encoding remain Tirta/Kochetkov's driver.
#pragma once
#include "AVCLanDrv.h"
#include "BuffSerial.h"
static bool benchLanCheck(){
  if(avclan.masterAddress!=avclan.headAddress || avclan.control!=0xF)return false;
  const bool direct=avclan.broadcast==AVC_MSG_DIRECT;
  const byte at=direct?1:0;
  if(avclan.dataSize!=at+3)return false;
  if(direct){if(avclan.slaveAddress!=avclan.deviceAddress || avclan.message[0])return false;}
  else if(avclan.slaveAddress!=0xFFF && avclan.slaveAddress!=0x1FF)return false;
  if(avclan.message[at]!=0x00 || avclan.message[at+1]!=0x01)return false;
  const byte request=avclan.message[at+2];
  if(request!=0x0A && request!=0x0C && request!=0x08)return false;
  bSerial.print("LAN_CHECK request=");bSerial.printHex8(request);
  bSerial.println("; response_from_Mockingboard; NAVI_ready_not_assumed");
  avclan.broadcast=AVC_MSG_DIRECT;
  avclan.masterAddress=avclan.deviceAddress;
  avclan.slaveAddress=avclan.headAddress;
  avclan.dataSize=request==0x08?4:5;
  avclan.message[0]=0x00;avclan.message[1]=0x01;avclan.message[2]=0x00;
  avclan.message[3]=request+0x10;
  avclan.message[4]=request==0x0A?0x01:0x00;
  avclan.sendMessage();
  return true;
}
