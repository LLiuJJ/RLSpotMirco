package shardctrler

import (
	"fmt"
	"time"
)

//
// Shard controler: assigns shards to replication groups.
//
// RPC interface:
// Join(servers) -- add a set of groups (gid -> server-list mapping).
// Leave(gids) -- delete a set of groups.
// Move(shard, gid) -- hand off one shard from current owner to gid.
// Query(num) -> fetch Config # num, or latest config if num==-1.
//
// A Config (configuration) describes a set of replica groups, and the
// replica group responsible for each shard. Configs are numbered. Config
// #0 is the initial configuration, with no groups and all shards
// assigned to group 0 (the invalid group).
//
// You will need to add fields to the RPC argument structs.
//

// The number of shards.
const NShards = 10

// A configuration -- an assignment of shards to groups.
// Please don't change this.
type Config struct {
	Num    int              // config number
	Shards [NShards]int     // shard -> gid
	Groups map[int][]string // gid -> servers[]
}

type Err uint8

const (
	OK Err = iota
	ErrWrongLeader
	ErrTimeout
)

func DefaultConfig() Config {
	return Config{Groups: make(map[int][]string)}
}

func (cfg Config) String() string {
	return fmt.Sprintf("Config(%v, %v, %v)", cfg.Num, cfg.Shards, cfg.Groups)
}

const ExecuteTimeout = 500 * time.Microsecond

const Debug = false

type Command struct {
	*CommandRequest
}

type OperationContext struct {
	MaxAppliedCommandId int64
	LastResponse        *CommandResponse
}

func (err Err) String() string {
	switch err {
	case OK:
		return "OK"
	case ErrWrongLeader:
		return "ErrWrongLeader"
	case ErrTimeout:
		return "ErrTimeout"
	default:
		return "ErrUnknown"
	}
}

type JoinArgs struct {
	Servers map[int][]string // new GID -> servers mappings
}

type JoinReply struct {
	WrongLeader bool
	Err         Err
}

type LeaveArgs struct {
	GIDs []int
}

type LeaveReply struct {
	WrongLeader bool
	Err         Err
}

type MoveArgs struct {
	Shard int
	GID   int
}

type MoveReply struct {
	WrongLeader bool
	Err         Err
}

type QueryArgs struct {
	Num int // desired config number
}

type QueryReply struct {
	WrongLeader bool
	Err         Err
	Config      Config
}

type OperationOp uint8

const (
	JoinOp OperationOp = iota
	LeaveOp
	MoveOp
	QueryOp
)

func (op OperationOp) String() string {
	switch op {
	case JoinOp:
		return "Join"
	case LeaveOp:
		return "Leave"
	case MoveOp:
		return "Move"
	case QueryOp:
		return "Query"
	default:
		return "Unknown"
	}

}

type CommandRequest struct {
	Servers   map[int][]string
	GIDs      []int
	Shard     int
	GID       int
	Num       int
	Op        OperationOp
	ClientId  int64
	CommandId int64
}

func (request CommandRequest) String() string {
	switch request.Op {
	case JoinOp:
		return fmt.Sprintf("Join(%v)", request.Servers)
	case LeaveOp:
		return fmt.Sprintf("Leave(%v)", request.GIDs)
	case MoveOp:
		return fmt.Sprintf("Move(%v, %v)", request.Shard, request.GID)
	case QueryOp:
		return fmt.Sprintf("Query(%v)", request.Num)
	}
	panic("Unknown operation")
}

type CommandResponse struct {
	Err    Err
	Config Config
}

func (response CommandResponse) String() string {
	return fmt.Sprintf("Response(%v)", response.Err)
}
