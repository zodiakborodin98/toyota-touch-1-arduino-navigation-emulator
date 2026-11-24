// Existing GadgetNutt CMD13 envelope, sent through the unchanged Tirta driver.
// Logical master 12 and physical 120 were measured on this head unit.
// Function list comes from the selected recorded profile, not a CY11 claim.
#pragma once
#include "AVCLanDrv.h"
#include "BuffSerial.h"
#include "NaviProfile.h"
static void benchAnnounce(byte logicalMaster){
  static const byte functions[] PROGMEM={NAVI_FUNCTION_BYTES};
  static const byte functionsNoB2[] PROGMEM={0xD4,0x6D,0xC6};
  avclan.broadcast=AVC_MSG_BROADCAST;avclan.masterAddress=avclan.deviceAddress;
  avclan.slaveAddress=0x1FF;avclan.dataSize=(navi_b2_advertised ? sizeof(functions) : sizeof(functionsNoB2))+3;
  avclan.message[0]=1;avclan.message[1]=logicalMaster;avclan.message[2]=0x13;
  if(navi_b2_advertised) memcpy_P(avclan.message+3,functions,sizeof(functions));
  else memcpy_P(avclan.message+3,functionsNoB2,sizeof(functionsNoB2));
  bSerial.println_p(PSTR("INITIATIVE_CMD13 existing_GadgetNutt_envelope"));
  avclan.sendMessage();
}
