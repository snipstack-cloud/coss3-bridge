      [*] = ;   // === BRIDGE LOOP: episode control, game side ===
      [*] = ;   // Lives here and not in the interface actor: reading files compiles
      [*] = ;   // only on this side. The interface is reached through GUIExecuteState,
      [*] = ;   // the same way lib/miscext3.script does it.
      [*] = ;   if (plind = GetPlayerIndexInterfaceIO) and (not _net_IsClient) and (not _net_IsReplay) then
      [*] = ;   begin
      [*] = ;      var hhb : Integer = ParserSelectByKey('br_hb');
      [*] = ;      var brhblast : Integer = -1000;
      [*] = ;      if (hhb = 0) then
      [*] = ;      hhb := ParserCreate('br_hb')
      [*] = ;      else
      [*] = ;      brhblast := ParserGetIntValueByKeyByHandle(hhb, 'realtime');
      [*] = ;      var brhbnow : Integer = Round(_misc_GetRealTime);
      [*] = ;      if ((brhbnow-brhblast) >= 5) or (brhbnow < brhblast) then
      [*] = ;      begin
      [*] = ;         ParserClearByHandle(hhb);
      [*] = ;         ParserSetIntValueByKeyByHandle(hhb, 'realtime', brhbnow);
      [*] = ;         ParserSetIntValueByKeyByHandle(hhb, 'gametime', Round(GetGameTime));
      [*] = ;         ParserSetIntValueByKeyByHandle(hhb, 'myplind', plind);
      [*] = ;         ParserSetIntValueByKeyByHandle(hhb, 'victory', gPlayer[plind].victorystate);
      [*] = ;         ParserSaveToFileByHandle(hhb, '@@OUT@@coss3_hb.dat');
      [*] = ;      end;
      [*] = ;      var brctlpath : String = '@@OUT@@coss3_ctl.dat';
      [*] = ;      if IsFileExists(brctlpath) then
      [*] = ;      begin
      [*] = ;         var hctl : Integer = ParserSelectByKey('br_ctl');
      [*] = ;         if (hctl = 0) then
      [*] = ;         hctl := ParserCreate('br_ctl');
      [*] = ;         ParserClearByHandle(hctl);
      [*] = ;         var brctlcmd : String;       // must live outside the block below
      [*] = ;         // Match settings for NEW. -1 means 'leave as is', so an old
      [*] = ;         // client that does not send them changes nothing.
      [*] = ;         var brctlres   : Integer = -1;   // gen.resourcestart: 0=1000 1=4000 2=5000
      [*] = ;         var brctlpeace : Integer = -1;   // additional.peacetime, default=0 minutes
      [*] = ;         var brctlai    : Integer = -1;   // aidifficulty: 3 = Impossible
      [*] = ;         // The UI list numbers levels from 1 (0 means 'slot open'),
      [*] = ;         // while aidifficulty holds one less: showcustomgame.inc:647
      [*] = ;         // sets the list index to aidifficulty+1. So Impossible is 3.
      [*] = ;         // Names come from locale/en/gui.txt: 0 None, 1 Normal,
      [*] = ;         // 2 Hard, 3 Very Hard, 4 Impossible.
      [*] = ;         var brctlnat   : String;         // country sid, 'net' = Netherlands
      [*] = ;         if ParserLoadFromFileByHandle(hctl, brctlpath) then
      [*] = ;         begin
      [*] = ;            brctlcmd := ParserGetValueByKeyByHandle(hctl, 'cmd');
      [*] = ;            if (ParserGetValueByKeyByHandle(hctl, 'res') <> '') then
      [*] = ;            brctlres := ParserGetIntValueByKeyByHandle(hctl, 'res');
      [*] = ;            if (ParserGetValueByKeyByHandle(hctl, 'peace') <> '') then
      [*] = ;            brctlpeace := ParserGetIntValueByKeyByHandle(hctl, 'peace');
      [*] = ;            if (ParserGetValueByKeyByHandle(hctl, 'ai') <> '') then
      [*] = ;            brctlai := ParserGetIntValueByKeyByHandle(hctl, 'ai');
      [*] = ;            brctlnat := ParserGetValueByKeyByHandle(hctl, 'nation');
      [*] = ;         end;
      [*] = ;         DeleteFileStream(brctlpath);
      [*] = ;         var back : Integer = ParserSelectByKey('br_ack');
      [*] = ;         if (back = 0) then
      [*] = ;         back := ParserCreate('br_ack');
      [*] = ;         ParserClearByHandle(back);
      [*] = ;         ParserSetValueByKeyByHandle(back, 'cmd', brctlcmd);
      [*] = ;         ParserSetIntValueByKeyByHandle(back, 'gametime', Round(GetGameTime));
      [*] = ;         ParserSetIntValueByKeyByHandle(back, 'myplind', plind);
      [*] = ;         ParserSetIntValueByKeyByHandle(back, 'victory', gPlayer[plind].victorystate);
      [*] = ;         ParserSetValueByKeyByHandle(back, 'done', 'ping');
      [*] = ;         if (brctlcmd = 'END') then
      [*] = ;         begin
      [*] = ;            gPlayer[plind].victorystate := gc_player_victorystate_lose;
      [*] = ;            if (gPlayer[plind].victorystategametime = 0) then
      [*] = ;            gPlayer[plind].victorystategametime := GetGameTime;
      [*] = ;            ParserSetValueByKeyByHandle(back, 'done', 'surrendered');
      [*] = ;         end;
      [*] = ;         if (brctlcmd = 'NEW') then
      [*] = ;         begin
      [*] = ;            // Match settings are applied HERE, before DoNewGame. Otherwise
      [*] = ;            // the game keeps whatever was left in the menu, and experiments
      [*] = ;            // become incomparable: on 12.09 that gave 5000 resources instead
      [*] = ;            // of 1000 and an enemy that already had 8 buildings.
      [*] = ;            // Numbers come from the game code, not from guessing:
      [*] = ;            //   resourcestart 0 -> 1000 (initmapgen.inc:167; 1->4000, 2->5000)
      [*] = ;            //   peacetime default -> 0 min (_misc_GetPeaceTime, misc.script:4264)
      [*] = ;            //   player fields -> gMap.players[i] (showcustomgame.inc)
      [*] = ;            if (brctlres >= 0) then
      [*] = ;            gMap.settings.gen.resourcestart := brctlres;
      [*] = ;            if (brctlpeace >= 0) then
      [*] = ;            gMap.settings.additional.peacetime := brctlpeace;
      [*] = ;            if (brctlai >= 0) then
      [*] = ;            begin
      [*] = ;               // Our slot: human, no adviser. Nation is set by string sid
      [*] = ;               // through _country_GetIDBySID so no id is hardcoded.
      [*] = ;               gMap.players[0].bexists := True;
      [*] = ;               gMap.players[0].bhuman := True;
      [*] = ;               gMap.players[0].bai := False;
      [*] = ;               gMap.players[0].bclosed := False;
      [*] = ;               gMap.players[0].team := 1;
      [*] = ;               if (brctlnat <> '') then
      [*] = ;               gMap.players[0].cid := _country_GetIDBySID(brctlnat);
      [*] = ;               // The opponent: computer of the requested difficulty.
      [*] = ;               gMap.players[1].bexists := True;
      [*] = ;               gMap.players[1].bhuman := False;
      [*] = ;               gMap.players[1].bai := True;
      [*] = ;               gMap.players[1].bclosed := False;
      [*] = ;               gMap.players[1].team := 2;
      [*] = ;               gMap.players[1].aidifficulty := brctlai;
      [*] = ;               if (brctlnat <> '') then
      [*] = ;               gMap.players[1].cid := _country_GetIDBySID(brctlnat);
      [*] = ;               // Close the rest: extra players change the conditions.
      [*] = ;               var brpl : Integer;
      [*] = ;               for brpl := 2 to gc_MaxPlayerCount-1 do
      [*] = ;               begin
      [*] = ;                  gMap.players[brpl].bexists := False;
      [*] = ;                  gMap.players[brpl].bclosed := True;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            ParserSetValueByKeyByHandle(back, 'done', 'newgame_called');
      [*] = ;            ParserSetIntValueByKeyByHandle(back, 'res', gMap.settings.gen.resourcestart);
      [*] = ;            ParserSetIntValueByKeyByHandle(back, 'peace', gMap.settings.additional.peacetime);
      [*] = ;            ParserSaveToFileByHandle(back, '@@OUT@@coss3_ack.dat');
      [*] = ;            GUIExecuteState('DoNewGame');
      [*] = ;         end;
      [*] = ;         ParserSaveToFileByHandle(back, '@@OUT@@coss3_ack.dat');
      [*] = ;      end;
      [*] = ;   end;
      [*] = ;   // === END BRIDGE LOOP ===