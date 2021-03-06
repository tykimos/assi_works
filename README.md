# 어시워크 assi_works

## 태스크와 워크

* 태스크 (= 업무) : 휴가, 출장, 조사 등등으로 하나의 업무 단위를 의미합니다.
* 워크오더 (= 작업지시서) : 하나의 태스크는 여러 워크오더로 구성됩니다. 휴가를 예를 들면, 신청, 검토, 기록 등등의 여러 작업으로 이뤄지며 각 작업은 특정 사람에게 할당되어 처리됩니다. 아무리 작은 일이라도 일은 일입니다. 이러한 일을 '워크'라고 부르며, '워크오더'에는 어떤 일을 할 지 기술된 작업 지시서입니다.
* 워크플로우 (= 작업흐름) : 특정 업무에 대해 사람들이 순서에 따라 할당받은 작업들을 수행하는 데, 이러한 작업들의 흐름을 '워크플로우'라고 합니다.

## 태스크

태스크는 아래 업무로 정의됩니다.

* 일반 (= task_general) : 별도의 양식없이 업무를 요청할 때 사용됩니다.
* 휴가 (= task_leave) : 연차, 병가 등등의 휴가 업무를 요청할 때 사용됩니다.

## 워크오더

### 워크오더 종류

워크오더의 종류(workorder type, wot)는 아래와 같습니다.

* 요청 (= wot_request)
* 검토 (= wot_confirm)
* 집행 (= wot_execute)
* 기록 (= wot_record)
* 참조 (= wot_cc)

### 워크오더 상태

워크오더는 아래의 상태(workorder status, wos)를 가지고 있습니다. 

* 생성 (= wos_null, -1)
* 예정 (= wos_scheduled, 0)   
* 대기 (= wos_wait, 1)
* 성공 (= wos_success, 2)
* 실패 (= wos_failure, 3)

## 워크플로우

워크플로우는 아래의 상태(workflow status, wfs)를 가지고 있습니다. 

* 생성 (= wfs_null, -1)
* 예정 (= wfs_scheduled, 0)   
* 대기 (= wfs_wait, 1)
* 성공 (= wfs_success, 2)
* 실패 (= wfs_failure, 3)