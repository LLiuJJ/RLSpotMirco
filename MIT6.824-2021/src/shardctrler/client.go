package shardctrler

//
// Shardctrler clerk.
//

import (
	"crypto/rand"
	"math/big"

	"6.824/labrpc"
)

type Clerk struct {
	servers   []*labrpc.ClientEnd
	leaderId  int64
	clientId  int64
	commandId int64
}

func nrand() int64 {
	max := big.NewInt(int64(1) << 62)
	bigx, _ := rand.Int(rand.Reader, max)
	return bigx.Int64()
}

func MakeClerk(servers []*labrpc.ClientEnd) *Clerk {
	return &Clerk{servers: servers, leaderId: 0, clientId: nrand(), commandId: 0}
}

func (ck *Clerk) Command(request *CommandRequest) Config {
	request.ClientId, request.CommandId = ck.clientId, ck.commandId
	for {
		var response CommandResponse
		if !ck.servers[ck.leaderId].Call("ShardCtrler.Command", request, &response) || response.Err == ErrWrongLeader || response.Err == ErrTimeout {
			ck.leaderId = (ck.leaderId + 1) % int64(len(ck.servers))
			continue
		}
		ck.commandId++
		return response.Config
	}
}

func (ck *Clerk) Query(num int) Config {
	return ck.Command(&CommandRequest{Op: QueryOp, Num: num})
}

func (ck *Clerk) Join(servers map[int][]string) {
	ck.Command(&CommandRequest{Op: JoinOp, Servers: servers})
}

func (ck *Clerk) Leave(gids []int) {
	ck.Command(&CommandRequest{Op: LeaveOp, GIDs: gids})
}

func (ck *Clerk) Move(shard int, gid int) {
	ck.Command(&CommandRequest{Op: MoveOp, Shard: shard, GID: gid})
}
