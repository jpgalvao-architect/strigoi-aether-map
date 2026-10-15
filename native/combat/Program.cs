// SPDX-License-Identifier: GPL-3.0-only
using System.Diagnostics;
using System.Collections.Concurrent;
using System.Net;
using System.Text.Json;
using System.Threading.Channels;
using AionMeter.Core.Capture;
using AionMeter.Core.Events;
using AionMeter.Core.Game;
using AionMeter.Core.Protocol;

if (args.Contains("--version")) { Console.WriteLine("Strigoi Combat Capture 1 / global-experimental / 0.9.0-beta.11"); return; }
if (args.Contains("--probe")) {
    Console.WriteLine(JsonSerializer.Serialize(new { protocol=1, npcap=OperatingSystem.IsWindows() && LiveCapture.IsNpcapInstalled(), saValidated=false }));
    return;
}
if (args.Contains("--self-test")) {
    var local=IPAddress.Loopback;
    var single=new[]{new GameConnection(local,123,local,456,10),new GameConnection(local,124,local,456,10)};
    if(GameProcessLocator.HasMultipleConnectedClients(single) || GameProcessLocator.HasMultipleConnectedClients([]) ||
       !GameProcessLocator.HasMultipleConnectedClients(single.Append(new GameConnection(local,125,local,456,20))))
        throw new Exception("Connected-client selection failed");
    var received = new List<byte>(); int gaps=0;
    var tcp = new TcpReassembler(d=>received.AddRange(d.ToArray()),()=>gaps++);
    tcp.Start(100); tcp.Push(100,new byte[]{1,2},0); tcp.Push(104,new byte[]{5,6},1);
    tcp.Push(102,new byte[]{3,4},2); tcp.Push(100,new byte[]{1,2},3);
    if (!received.SequenceEqual(new byte[]{1,2,3,4,5,6}) || gaps!=0) throw new Exception("TCP reassembly failed");
    var events=new List<GameEvent>(); var parser=new PacketParser(GameData.Empty,events.Add);
    var body=new List<byte>{50,4,0,1}; body.AddRange(BitConverter.GetBytes((uint)11020000));
    body.AddRange(new byte[10]); body.AddRange(new byte[]{0x80,0x7d,100,1}); // scalar 16000, damage 100, tail 1
    parser.Handle(Opcodes.Damage,body.ToArray());
    if(events.Count!=1 || events[0] is not DamageEvent {SourceId:1,TargetId:50,Damage:100}) throw new Exception("Synthetic damage parser test failed");
    parser.Handle(Opcodes.Damage,new byte[]{0xff});
    if(parser.DamageRejected!=1) throw new Exception("Malformed damage was not rejected");
    var identity=new List<byte>{2,0,0,0,0,1,8};
    identity.AddRange(System.Text.Encoding.UTF8.GetBytes("FixtureB"));
    identity.AddRange(BitConverter.GetBytes((uint)9)); identity.AddRange(new byte[2]);
    parser.Handle(Opcodes.PlayerInfo,identity.ToArray());
    if(!events.OfType<PlayerSeenEvent>().Any(e=>e.ActorId==2 && e.ServerId==0 && e.Class==GameClass.Templar))
        throw new Exception("Serverless player identity failed");
    var roster=new List<byte>(new byte[4]); roster.Add(0); roster.Add(2);
    roster.AddRange(new byte[17]); roster.Add(2); // two expected members
    roster.AddRange(new byte[8]); roster.AddRange(BitConverter.GetBytes((ushort)1001));
    roster.Add(8); roster.AddRange(System.Text.Encoding.UTF8.GetBytes("FixtureB"));
    roster.AddRange(BitConverter.GetBytes((uint)9)); roster.AddRange(BitConverter.GetBytes((uint)45));
    roster.AddRange(BitConverter.GetBytes((uint)1000));
    roster.AddRange(BitConverter.GetBytes((ushort)1001)); roster.AddRange(new byte[3]);
    roster.AddRange(BitConverter.GetBytes((ulong)10000));
    parser.Handle(Opcodes.PartyRoster,roster.ToArray());
    if(!events.OfType<PartyRosterEvent>().Any(e=>e.Members.Count==1 && !e.Complete))
        throw new Exception("Partial roster detection failed");
    static List<byte> Group(int count)
    {
        var bytes=new List<byte>(new byte[4]);bytes.Add(0);bytes.Add((byte)count);
        bytes.AddRange(new byte[17]);bytes.Add((byte)count);return bytes;
    }
    static void Member(List<byte> bytes,byte slot,string name,ushort server,uint job,bool badPower=false,int tail=0)
    {
        bytes.Add(30);bytes.Add(slot);bytes.AddRange(new byte[6]);
        bytes.AddRange(BitConverter.GetBytes(server));bytes.Add((byte)name.Length);
        bytes.AddRange(System.Text.Encoding.UTF8.GetBytes(name));
        bytes.AddRange(BitConverter.GetBytes(job));bytes.AddRange(BitConverter.GetBytes((uint)45));
        bytes.AddRange(BitConverter.GetBytes((uint)1000));bytes.AddRange(BitConverter.GetBytes(server));
        bytes.AddRange(new byte[3]);bytes.AddRange(BitConverter.GetBytes(badPower?ulong.MaxValue:10000UL));
        bytes.AddRange(Enumerable.Repeat((byte)0xee,tail));
    }
    var five=Group(5);
    Member(five,0,"Alpha",2401,5,tail:60);Member(five,1,"Beta",2401,17);
    Member(five,2,"Gamma",2402,21,badPower:true);Member(five,3,"Delta",1402,29);
    Member(five,4,"Epsilon",1501,33);
    parser.Handle(Opcodes.PartyRoster,five.ToArray());
    if(!events.OfType<PartyRosterEvent>().Any(e=>e.Complete && e.Members.Count==5 && e.Members[2].CombatPower==0))
        throw new Exception("Optional metadata/long tails truncated five-member roster");
    var vacant=Group(3);vacant.AddRange(new byte[11]);
    Member(vacant,1,"Alpha",2401,5);Member(vacant,2,"Beta",1402,29);
    parser.Handle(Opcodes.PartyRoster,vacant.ToArray());
    if(!events.OfType<PartyRosterEvent>().Any(e=>e.Complete && e.Members.Count==2))
        throw new Exception("Vacant first slot hid later members");
    var unread=Group(3);unread.AddRange(new byte[]{30,0,0,0,0,0,0,0,0,0,255});
    unread.AddRange(new byte[20]);Member(unread,1,"Alpha",2401,5);Member(unread,2,"Beta",1402,29);
    parser.Handle(Opcodes.PartyRoster,unread.ToArray());
    if(!events.OfType<PartyRosterEvent>().Any(e=>!e.Complete && e.Members.Count==2))
        throw new Exception("Unread first member hid valid later members");
    var namedSpirit=new List<byte>{7,0x1C,0,0,0,1,8};
    namedSpirit.AddRange(System.Text.Encoding.UTF8.GetBytes("FixtureB"));
    namedSpirit.AddRange(new byte[]{0x80,0x75,0xD5,0x2A,0xBB,0x03,0,0,2});
    parser.Handle(Opcodes.Spawn,namedSpirit.ToArray());
    if(!events.OfType<SummonSeenEvent>().Any(e=>e.ActorId==7 && e.OwnerId==2 && e.OwnerName=="FixtureB"))
        throw new Exception("Spirit anchored owner must take priority over inline name");
    parser.Handle(Opcodes.Spawn,new byte[]{8,0x1C,0,0,0,0});
    if(!events.OfType<SummonSeenEvent>().Any(e=>e.ActorId==8 && e.OwnerId==0))
        throw new Exception("Ownerless summon kind 1C was dropped");
    var cast=new List<byte>{2,0};cast.AddRange(BitConverter.GetBytes((uint)16280140));
    cast.AddRange(new byte[]{0,0,50});parser.Handle(Opcodes.Cast,cast.ToArray());
    if(!events.OfType<CastEvent>().Any(e=>e.ActorId==2 && e.SkillCode==16280140 && e.TargetId==50))
        throw new Exception("Raw cast variant was lost");
    if(!events.OfType<DamageEvent>().Any(e=>e.PowerScalar==16000))throw new Exception("Damage scalar was lost");
    var pets = new List<byte>(new byte[4]); pets.Add(1);
    pets.AddRange(BitConverter.GetBytes((uint)1127)); pets.AddRange(new byte[4]);
    pets.AddRange(BitConverter.GetBytes((uint)2)); pets.Add(1);
    pets.AddRange(BitConverter.GetBytes((uint)1127)); pets.AddRange(BitConverter.GetBytes((uint)9));
    parser.Handle(Opcodes.PetCollection,pets.ToArray());
    if(!events.OfType<PetCollectionEvent>().Any(e=>e.Levels.Single()==new PetLevelInfo(1127,2) &&
       e.Souls.Single()==new PetSoulInfo(1127,9))) throw new Exception("Pet collection fixture failed");
    var petCount=events.OfType<PetCollectionEvent>().Count();
    for(int n=0;n<pets.Count;n++) parser.Handle(Opcodes.PetCollection,pets.Take(n).ToArray());
    var invalidPet=pets.ToArray(); invalidPet[5]=0;invalidPet[6]=0;invalidPet[7]=0;invalidPet[8]=0;
    parser.Handle(Opcodes.PetCollection,invalidPet);
    var duplicate=new List<byte>(new byte[4]); duplicate.Add(2);
    duplicate.AddRange(pets.Skip(5).Take(12));duplicate.AddRange(pets.Skip(5).Take(12));duplicate.Add(0);
    parser.Handle(Opcodes.PetCollection,duplicate.ToArray());
    if(events.OfType<PetCollectionEvent>().Count()!=petCount || parser.PetsRejected!=pets.Count+2)
        throw new Exception("Truncated/invalid/duplicate pets were accepted");
    var soul=new List<byte>{0};soul.AddRange(BitConverter.GetBytes((uint)1127));soul.AddRange(BitConverter.GetBytes((uint)1));
    parser.Handle(Opcodes.PetSoulAcquired,soul.ToArray());
    var insight=new List<byte>{0,0};insight.AddRange(BitConverter.GetBytes((uint)1127));insight.AddRange(BitConverter.GetBytes((uint)3));
    parser.Handle(Opcodes.PetLevelReached,insight.ToArray());
    if(!events.OfType<PetSoulAcquiredEvent>().Any(e=>e.PetId==1127 && e.Amount==1) ||
       !events.OfType<PetLevelReachedEvent>().Any(e=>e.PetId==1127 && e.Level==3)) throw new Exception("Pet deltas failed");
    parser.Handle(Opcodes.PetCollection,new byte[]{0,0,0,0,0,0});
    if(!events.OfType<PetCollectionEvent>().Any(e=>e.Levels.Count==0 && e.Souls.Count==0))
        throw new Exception("Empty pet collection failed");
    Console.WriteLine("SELF_TEST_OK: connected clients, TCP, damage, malformed record, serverless identity, partial/full roster, optional stats, vacant/unread slots, spirit owner, raw cast, scalar, pet snapshot/deltas, empty/truncated/invalid/duplicate pet records; no capture"); return;
}
var diagnostic=args.Contains("--diagnose");
var diagnosticSeconds=10;
var durationArgument=Array.IndexOf(args,"--seconds");
if(durationArgument>=0 && (!diagnostic || durationArgument+1>=args.Length ||
    !int.TryParse(args[durationArgument+1],out diagnosticSeconds) || diagnosticSeconds is < 1 or > 600)) {
    Console.Error.WriteLine("Diagnostic duration must be between 1 and 600 seconds."); Environment.ExitCode=2; return;
}
if (!args.Contains("--live") && !diagnostic) { Console.Error.WriteLine("Use --probe, --version, --self-test, --diagnose or --live"); Environment.ExitCode=2; return; }
if (!OperatingSystem.IsWindows() || !LiveCapture.IsNpcapInstalled()) {
    Console.WriteLine(JsonSerializer.Serialize(new {type="status", code="missing_npcap"})); Environment.ExitCode=3; return;
}
// No recorder, sender, updater, online metadata or raw-packet output is constructed.
var queue=Channel.CreateBounded<object>(new BoundedChannelOptions(5000) {SingleReader=true, FullMode=BoundedChannelFullMode.Wait});
long lost=0, sequence=0; var session=Guid.NewGuid().ToString("N"); var clock=Stopwatch.StartNew();
var diagnosticCounts=new ConcurrentDictionary<string,long>();
void Send(object message) { if (!queue.Writer.TryWrite(message)) Interlocked.Increment(ref lost); }
using var capture=new LiveCapture(GameData.Empty, new LiveCaptureOptions());
Send(new {type="hello", protocol=1, parser="global-414de5c-experimental", saValidated=false});
capture.StatusChanged += status=>Send(new {type="status", code=status.State.ToString(),
    reason=status.State==CaptureState.Error ? ErrorReason(status.Message) : null,
    reset_zone=status.State is CaptureState.Starting or CaptureState.Stopped or CaptureState.Error ||
        (status.State==CaptureState.WaitingForGame &&
         !status.Message.StartsWith("Connected ·") && !status.Message.StartsWith("Listening on")),
    detail=diagnostic && status.State==CaptureState.Error ? status.Message : null,
    packets=status.Packets, events=status.Events});
capture.EventDecoded += ev=> {
    if(diagnostic) {
        diagnosticCounts.AddOrUpdate(ev.GetType().Name,1,(_,count)=>count+1);
        if(ev is ZoneChangedEvent zone)
            Send(new {type="diagnostic_zone", map_id=zone.MapId, dungeon=zone.IsDungeon, teleport=zone.IsTeleport});
        else if(ev is InstanceTimerEvent timer)
            Send(new {type="diagnostic_timer", map_id=timer.MapId, kind=timer.Kind});
        return; // Diagnostics expose counters only: no player names, events or packet bytes.
    }
    if (ev is not (DamageEvent or SelfIdentifiedEvent or PlayerSeenEvent or PartyRosterEvent or NpcSeenEvent or
        SummonSeenEvent or CastEvent or DeathEvent or ZoneChangedEvent or HitNoticeEvent or InstanceTimerEvent or
        PetCollectionEvent or PetSoulAcquiredEvent or PetLevelReachedEvent)) return;
    // FieldBossListEvent.Raw and all uninterpreted bytes are deliberately excluded.
    Send(new {type="event", session, sequence=Interlocked.Increment(ref sequence), time_ms=(long)clock.Elapsed.TotalMilliseconds,
        kind=ev.GetType().Name, payload=JsonSerializer.SerializeToElement(ev,ev.GetType())});
};
var writer=Task.Run(async ()=>{await foreach(var item in queue.Reader.ReadAllAsync()) {
    await Console.Out.WriteLineAsync(JsonSerializer.Serialize(item));
}});
capture.Start();
using var cancel=new CancellationTokenSource();
if(diagnostic) cancel.CancelAfter(diagnosticSeconds*1000);
Console.CancelKeyPress += (_,e)=>{e.Cancel=true;cancel.Cancel();};
_ = Task.Run(async ()=>{ while(await Console.In.ReadLineAsync() is { } command) if(command=="stop") {cancel.Cancel();return;} cancel.Cancel(); });
try {
    while(!cancel.IsCancellationRequested) {
        await Task.Delay(1000,cancel.Token);
        var health=capture.Health(); var pipeline=capture.Pipeline;
        Send(new {type="health", time_ms=(long)clock.Elapsed.TotalMilliseconds, dropped=Interlocked.Read(ref lost)+(health?.Dropped ?? 0), gaps=pipeline.Gaps, pets_rejected=pipeline.Parser.PetsRejected,
            rejected=pipeline.Parser.DamageRejected, flows=pipeline.GameFlows, packets=capture.Status.Packets});
    }
} catch(OperationCanceledException) { }
finally {
    capture.Stop();
    if(diagnostic) Send(new {type="diagnostic",counts=diagnosticCounts});
    queue.Writer.TryComplete();await writer;
}

static string ErrorReason(string message) => message.StartsWith("More than one connected") ? "multiple_clients" :
    message.StartsWith("No Npcap adapter") ? "adapter_not_found" :
    message.StartsWith("Npcap is not installed") ? "npcap_load_failed" : "capture_failed";
