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
      [*] = ;         // additional.balloon: 0 as usual, 1 forbidden, 2 GIVEN TO ALL.
      [*] = ;         // With 2 the fog of war is off for everyone - _player_UpdateFOW
      [*] = ;         // (player.script:456) skips AddFOWPlayers when balloon=with.
      [*] = ;         // A MATCH SETTING, not a cheat, and it decides whether the bridge
      [*] = ;         // may tell the model what the enemy has: on an open map a human
      [*] = ;         // sees it too.
      [*] = ;         var brctlball  : Integer = -1;
      [*] = ;         // additional.cannons: 1 = no cannons, towers and walls for ANYONE
      [*] = ;         // (player.script:2703 clears bproduceenabled for mortars and guns
      [*] = ;         // and disables the artillery upgrades).
      [*] = ;         var brctlcann  : Integer = -1;
      [*] = ;         // additional.capture: 1 no peasants, 2 no peasants and centres,
      [*] = ;         // 3 artillery only. This one touches our own measure: by default a
      [*] = ;         // peasant can be CAPTURED instead of killed, and he leaves the
      [*] = ;         // enemy count all the same - so 'goal taken' could mean a capture.
      [*] = ;         var brctlcapt  : Integer = -1;
      [*] = ;         if ParserLoadFromFileByHandle(hctl, brctlpath) then
      [*] = ;         begin
      [*] = ;            brctlcmd := ParserGetValueByKeyByHandle(hctl, 'cmd');
      [*] = ;            if (ParserGetValueByKeyByHandle(hctl, 'res') <> '') then
      [*] = ;            brctlres := ParserGetIntValueByKeyByHandle(hctl, 'res');
      [*] = ;            if (ParserGetValueByKeyByHandle(hctl, 'peace') <> '') then
      [*] = ;            brctlpeace := ParserGetIntValueByKeyByHandle(hctl, 'peace');
      [*] = ;            if (ParserGetValueByKeyByHandle(hctl, 'ai') <> '') then
      [*] = ;            brctlai := ParserGetIntValueByKeyByHandle(hctl, 'ai');
      [*] = ;            if (ParserGetValueByKeyByHandle(hctl, 'balloon') <> '') then
      [*] = ;            brctlball := ParserGetIntValueByKeyByHandle(hctl, 'balloon');
      [*] = ;            if (ParserGetValueByKeyByHandle(hctl, 'cannons') <> '') then
      [*] = ;            brctlcann := ParserGetIntValueByKeyByHandle(hctl, 'cannons');
      [*] = ;            if (ParserGetValueByKeyByHandle(hctl, 'capture') <> '') then
      [*] = ;            brctlcapt := ParserGetIntValueByKeyByHandle(hctl, 'capture');
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
      [*] = ;            if (brctlball >= 0) then
      [*] = ;            gMap.settings.additional.balloon := brctlball;
      [*] = ;            if (brctlcann >= 0) then
      [*] = ;            gMap.settings.additional.cannons := brctlcann;
      [*] = ;            if (brctlcapt >= 0) then
      [*] = ;            gMap.settings.additional.capture := brctlcapt;
      [*] = ;            if (brctlai >= 0) then
      [*] = ;            begin
      [*] = ;               // Do NOT rewrite the human slot as a whole. The first version
      [*] = ;               // set bexists/bhuman/bai/team on it and wiped what the game
      [*] = ;               // puts there from the profile: the name and identity. The slot
      [*] = ;               // became nameless and the nation showed as 'unknown'. The menu
      [*] = ;               // has already set that slot up, so touch only the nation.
      [*] = ;               if (brctlnat <> '') then
      [*] = ;               gMap.players[0].cid := _country_GetIDBySID(brctlnat);
      [*] = ;               gMap.players[0].team := 1;
      [*] = ;               // The opponent slot has to be created in full.
      [*] = ;               gMap.players[1].bexists := True;
      [*] = ;               gMap.players[1].bhuman := False;
      [*] = ;               gMap.players[1].bai := True;
      [*] = ;               gMap.players[1].bclosed := False;
      [*] = ;               gMap.players[1].bready := True;
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
      [*] = ;            // Report what actually happened: without it there is no way to
      [*] = ;            // tell 'was not applied' from 'applied, then overridden'.
      [*] = ;            ParserSetIntValueByKeyByHandle(back, 'nat0', gMap.players[0].cid);
      [*] = ;            ParserSetIntValueByKeyByHandle(back, 'nat1', gMap.players[1].cid);
      [*] = ;            ParserSetIntValueByKeyByHandle(back, 'ai1', gMap.players[1].aidifficulty);
      [*] = ;            ParserSetValueByKeyByHandle(back, 'done', 'newgame_called');
      [*] = ;            ParserSetIntValueByKeyByHandle(back, 'res', gMap.settings.gen.resourcestart);
      [*] = ;            ParserSetIntValueByKeyByHandle(back, 'peace', gMap.settings.additional.peacetime);
      [*] = ;            ParserSetIntValueByKeyByHandle(back, 'balloon', gMap.settings.additional.balloon);
      [*] = ;            ParserSetIntValueByKeyByHandle(back, 'cannons', gMap.settings.additional.cannons);
      [*] = ;            ParserSetIntValueByKeyByHandle(back, 'capture', gMap.settings.additional.capture);
      [*] = ;            ParserSaveToFileByHandle(back, '@@OUT@@coss3_ack.dat');
      [*] = ;            GUIExecuteState('DoNewGame');
      [*] = ;         end;
      [*] = ;         ParserSaveToFileByHandle(back, '@@OUT@@coss3_ack.dat');
      [*] = ;      end;
      [*] = ;   end;
      [*] = ;   // === END BRIDGE LOOP ===