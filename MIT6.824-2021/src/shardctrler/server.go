package shardctrler

import (
	"sync"
	"sync/atomic"
	"time"

	"6.824/labgob"
	"6.824/labrpc"
	"6.824/raft"
)

type ShardCtrler struct {
	mu      sync.RWMutex
	dead    int32
	rf      *raft.Raft
	applyCh chan raft.ApplyMsg

	stateMachine   ConfigStateMachine
	lastOperations map[int64]OperationContext
	notifyChans    map[int]chan *CommandResponse
}

func (sc *ShardCtrler) Command(request *CommandRequest, response *CommandResponse) {
	sc.mu.RLock()
	if request.Op != QueryOp && sc.isDuplicateRequest(request.ClientId, request.CommandId) {
		LastResponse := sc.lastOperations[request.ClientId].LastResponse
		response.Config, response.Err = LastResponse.Config, LastResponse.Err
		sc.mu.RUnlock()
		return
	}
	sc.mu.RUnlock()
	index, _, isLeader := sc.rf.Start(Command{request})
	if !isLeader {
		response.Err = ErrWrongLeader
		return
	}
	sc.mu.Lock()
	ch := sc.getNotifyChan(index)
	sc.mu.Unlock()
	select {
	case result := <-ch:
		response.Config, response.Err = result.Config, result.Err
	case <-time.After(ExecuteTimeout):
		response.Err = ErrTimeout
	}

	go func() {
		sc.mu.Lock()
		sc.removeOutdateNotifyChan(index)
		sc.mu.Unlock()
	}()
}

func (sc *ShardCtrler) isDuplicateRequest(clientId int64, requestId int64) bool {
	operationContext, ok := sc.lastOperations[clientId]
	return ok && requestId <= operationContext.MaxAppliedCommandId
}

// the tester calls Kill() when a ShardCtrler instance won't
// be needed again. you are not required to do anything
// in Kill(), but it might be convenient to (for example)
// turn off debug output from this instance.
func (sc *ShardCtrler) Kill() {
	atomic.StoreInt32(&sc.dead, 1)
	sc.rf.Kill()
}

func (sc *ShardCtrler) killed() bool {
	return atomic.LoadInt32(&sc.dead) == 1
}

// needed by shardkv tester
func (sc *ShardCtrler) Raft() *raft.Raft {
	return sc.rf
}

func (sc *ShardCtrler) getNotifyChan(index int) chan *CommandResponse {
	if _, ok := sc.notifyChans[index]; !ok {
		sc.notifyChans[index] = make(chan *CommandResponse, 1)
	}
	return sc.notifyChans[index]
}

func (sc *ShardCtrler) removeOutdateNotifyChan(index int) {
	delete(sc.notifyChans, index)
}

func (sc *ShardCtrler) applyLogToStm(command Command) *CommandResponse {
	var config Config
	var err Err
	switch command.Op {
	case JoinOp:
		err = sc.stateMachine.Join(command.Servers)
	case LeaveOp:
		err = sc.stateMachine.Leave(command.GIDs)
	case MoveOp:
		err = sc.stateMachine.Move(command.Shard, command.GID)
	case QueryOp:
		config, err = sc.stateMachine.Query(command.Num)
	}
	return &CommandResponse{err, config}
}

func (sc *ShardCtrler) applier() {
	for sc.killed() == false {
		select {
		case message := <-sc.applyCh:
			if message.CommandValid {
				var response *CommandResponse
				command := message.Command.(Command)
				sc.mu.Lock()

				if command.Op != QueryOp && sc.isDuplicateRequest(command.ClientId, command.CommandId) {
					response = sc.lastOperations[command.ClientId].LastResponse
				} else {
					response = sc.applyLogToStm(command)
					if command.Op != QueryOp {
						sc.lastOperations[command.ClientId] = OperationContext{command.CommandId, response}
					}
				}

				if currentTerm, isLeader := sc.rf.GetState(); isLeader && message.CommandTerm == currentTerm {
					ch := sc.getNotifyChan(message.CommandIndex)
					ch <- response
				}

				sc.mu.Unlock()
			} else {
				panic("raft apply invalid command")
			}
		}
	}
}

// servers[] contains the ports of the set of
// servers that will cooperate via Paxos to
// form the fault-tolerant shardctrler service.
// me is the index of the current server in servers[].
func StartServer(servers []*labrpc.ClientEnd, me int, persister *raft.Persister) *ShardCtrler {
	labgob.Register(Command{})
	applyCh := make(chan raft.ApplyMsg)

	sc := &ShardCtrler{
		applyCh:        applyCh,
		dead:           0,
		rf:             raft.Make(servers, me, persister, applyCh),
		stateMachine:   NewMemoryConfigStateMachines(),
		lastOperations: make(map[int64]OperationContext),
		notifyChans:    make(map[int]chan *CommandResponse),
	}

	go sc.applier()

	return sc
}
