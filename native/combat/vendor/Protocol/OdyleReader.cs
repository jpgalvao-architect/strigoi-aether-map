// SPDX-License-Identifier: GPL-3.0-only
// Layout reference and attribution: ODyle-PROTOCOL-NOTICE.md.
namespace AionMeter.Core.Protocol;

public readonly record struct OdyleReading(uint Basic, uint Charged, uint Key);

public static class OdyleReader
{
    private readonly record struct Entry(byte Mask, byte Slot, uint Key, uint First, uint Second, int Next);

    private static bool Number(ReadOnlySpan<byte> body, ref int offset, out uint value)
    {
        value=0;
        for(int n=0;n<5;n++) {
            if(offset>=body.Length)return false;
            var b=body[offset++];
            if(n==4 && (b&0xf0)!=0)return false;
            value|=(uint)(b&0x7f)<<(n*7);
            if((b&0x80)==0)return true;
        }
        return false;
    }

    private static bool ReadEntry(ReadOnlySpan<byte> body,int at,out Entry entry)
    {
        entry=default;
        if(at<0 || at+2>body.Length)return false;
        var mask=body[at++];var slot=body[at++];
        if(mask is not (4 or 8 or 12) || !Number(body,ref at,out var key))return false;
        uint first=0,second=0;
        if((mask&4)!=0 && !Number(body,ref at,out first))return false;
        if((mask&8)!=0 && !Number(body,ref at,out second))return false;
        entry=new(mask,slot,key,first,second,at);
        return true;
    }

    private static bool Energy(Entry entry,out OdyleReading reading)
    {
        reading=default;
        if(entry.Slot!=1 || entry.Key==0 || entry.First>100000 || entry.Second>100000)return false;
        reading=new(entry.First,entry.Second,entry.Key);return true;
    }

    public static bool Snapshot(ReadOnlySpan<byte> body,out OdyleReading reading)
    {
        reading=default;bool found=false;
        if(body.Length>65536)return false;
        for(int at=0;at+2<body.Length;at++) {
            if(body[at+1]!=1 || !ReadEntry(body,at,out var first) || !Energy(first,out var candidate) ||
               !ReadEntry(body,first.Next,out var next) || next.Slot!=2 || next.Key!=first.Key)continue;
            if(found)return false; // Ambiguous lists never become a balance.
            reading=candidate;found=true;
            at=first.Next-1;
        }
        return found;
    }

    public static bool Update(ReadOnlySpan<byte> body,uint key,out OdyleReading reading)
    {
        reading=default;
        if(body.Length<2 || body.Length>65536 || key==0 || body[0]>128)return false;
        int at=1,count=Math.Max(1,(int)body[0]);bool found=false;
        for(int n=0;n<count;n++) {
            if(!ReadEntry(body,at,out var entry))return false;
            at=entry.Next;
            if(entry.Slot!=1 || entry.Key!=key)continue;
            if(found || !Energy(entry,out reading))return false;
            found=true;
        }
        return found;
    }
}
