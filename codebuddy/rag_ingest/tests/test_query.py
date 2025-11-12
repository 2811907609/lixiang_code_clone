from rag_ingest.query import query, rerank_scores


def test_rerank():
    q = 'hi'
    candidates = ['hello', 'I am fine', '你好么', 'hello world']
    scores = rerank_scores(q, candidates=candidates)
    print('scores', scores)


def test_query_go():
    namespace = 'gitlabee_chehejia_com_ep_integration_codebuddy_agent_git'
    testcases = [
        dict(q='''
这个仓库是干嘛的? 介绍下这个仓库.
''',),
        dict(q='''
func (h *EventHandler) Match(evt *models.CommonEvent) bool {
	if h.EventSource != evt.EventSource {
		return false
	}
	if h.EventTypeRegex != "" {
		matched := h.eventTypeRegexCompile.MatchString(evt.EventType)
		if !matched {
			return false
		}
	}
	if h.ProjectRegex != "" {
		matched := h.projectRegexCompile.MatchString(evt.EventProject)
		if !matched {
			return false
		}
	}
	return true
}
''',),
        dict(q='''
找出跟下面这段代码相关的结构体.

func BuildProjectStartByteField(sheetStruct *models.VehicleConfigCode, fieldValue string) {
	if fieldValue != "" {
		sheetStruct.ProjectStartByte = fieldValue
	}
}
''',),
        dict(q='''
    It("transit to makeMCoreNoCalRelease", func() {
		x.XCURelease.Status = "created"
		err := s.DB.Save(x.XCURelease).Error
		Expect(err).ShouldNot(HaveOccurred())
		mType := "makeNew"
		x.XCURelease.MCoreRelateType = &mType
		err = s.XcuReleaseTransit(x.XCURelease.ID, "makeMCoreNoCalRelease", &x, 1)
		Expect(err).ShouldNot(HaveOccurred())
	})
这段函数在测试什么？
''',),
        dict(q='''
GetUserIDByTokenV2 这个函数怎么使用?
''',),
        dict(q='''
GetUserIDByTokenV2 这个函数怎么使用?
''',),
    ]
    for tc in testcases:
        q = tc['q']
        records, stat = query(
            q,
            namespace=namespace,
            # categories=['split.llama_index'],
            rerank_limit=10)
        for record in records:
            print(
                f'query == distance {record.distance} == rerank score {record.rerank_score}===\n',
                record.payload['content'])
        print(f'query stat {stat}')
        break
