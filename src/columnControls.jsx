
import * as d3 from 'd3';
import React, { Component } from 'react';
import { Button } from "@blueprintjs/core";


class ColumnControls extends Component {

    constructor (props) {
        super(props);
        this.state = {};
    }


    render() {

        return (
            <div className="">
                {this.props.columnGroups.map((group, index) => (
                        <div key={index}>
                            <div className="pt3 b">{group.name}</div>
                            <ColumnGroupButtons group={group} {...this.props}/>
                        </div>
                ))}
            </div>
        );
    }
}


class ColumnGroupButtons extends Component {
    constructor (props) {
        super(props);
    }

    render() {
        return this.props.group.ids.map(id => {
            const def = this.props.columnDefs.filter(def => def.id===id).pop();
            if (!def) return (<div>{id}</div>);
            return (
                <div className="">
                    <Button 
                        fill minimal
                        alignText='left'
                        active={def.selected} 
                        onClick={d => this.props.toggleColumn(def.id)} 
                        text={def.Header}/>
                </div>
            );
        });
    }
}

export default ColumnControls;